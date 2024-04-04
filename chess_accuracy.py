import io
import math
import sys
import traceback

import chess.engine
import chess.pgn


def get_eval_str(score, board):
    if score.is_mate():
        if score.relative.mate() > 0:
            mating_side = "White" if board.turn else "Black"
        else:
            mating_side = "Black" if board.turn else "White"
        return "Mate in " + str(abs(score.relative.mate())) + " for " + mating_side
    else:
        return str(score.white().score() / 100.0)


def move_accuracy_percent(before, after):
    if after >= before:
        return 100.0
    else:
        win_diff = before - after
        raw = 103.1668100711649 * math.exp(-0.04354415386753951 * win_diff) + -3.166924740191411
        return max(min(raw + 1, 100), 0)


def winning_chances_percent(cp):
    multiplier = -0.00368208
    chances = 2 / (1 + math.exp(multiplier * cp)) - 1
    return 50 + 50 * max(min(chances, 1), -1)


def harmonic_mean(values):
    n = len(values)
    if n == 0:
        return 0
    reciprocal_sum = sum(1 / x for x in values if x)
    return n / reciprocal_sum if reciprocal_sum else 0


def std_dev(seq):
    if len(seq) == 0:
        return 0.5  # Return the minimum weight if sub-sequence is empty
    mean = sum(seq) / len(seq)
    variance = sum((x - mean) ** 2 for x in seq) / len(seq)
    return math.sqrt(variance)


def volatility_weighted_mean(accuracies, win_chances, is_white):
    weights = []
    for i in range(len(accuracies)):
        base_index = i * 2 + 1 if is_white else i * 2 + 2
        start_idx = max(base_index - 2, 0)
        end_idx = min(base_index + 2, len(win_chances) - 1)

        sub_seq = win_chances[start_idx:end_idx]
        weight = max(min(std_dev(sub_seq), 12), 0.5)
        weights.append(weight)

    weighted_sum = sum(accuracies[i] * weights[i] for i in range(len(accuracies)))
    total_weight = sum(weights)
    weighted_mean = weighted_sum / total_weight if total_weight else 0

    return weighted_mean


def process(file, engine, depth, is_verbose, board):
    accuracies_white, accuracies_black, win_chances = [], [], []
    total_cp_loss_white, total_cp_loss_black = 0, 0
    prev_evaluation = 17
    move_number = 1

    win_chances.append(winning_chances_percent(prev_evaluation))

    while True:
        game = chess.pgn.read_game(file)
        if game is None:
            break

        node = game
        while not node.is_end():
            if node.move is not None:
                san_move = board.san(node.move)
                board.push(node.move)
                result = engine.analyse(board, chess.engine.Limit(depth=depth))
                score = result["score"].white().score(mate_score=1000)

                win_before_white = winning_chances_percent(prev_evaluation)
                win_after_white = winning_chances_percent(score)
                win_chances.append(win_after_white)

                if board.turn == chess.WHITE:
                    win_before = 100 - win_before_white
                    win_after = 100 - win_after_white
                else:
                    win_before = win_before_white
                    win_after = win_after_white

                accuracy = move_accuracy_percent(win_before, win_after)

                if board.turn == chess.BLACK:
                    cp_loss = 0 if score > prev_evaluation else prev_evaluation - score
                    total_cp_loss_white += cp_loss
                    accuracies_white.append(accuracy)
                else:
                    cp_loss = 0 if score < prev_evaluation else score - prev_evaluation
                    total_cp_loss_black += cp_loss
                    accuracies_black.append(accuracy)

                if is_verbose:
                    move_number_str = f'{move_number:3}.' if board.turn == chess.BLACK else "    "
                    print(
                        f'{move_number_str} {san_move:5}: Eval: {get_eval_str(result["score"], board):5}, '
                        f'Centipawn Loss: {cp_loss:3}, Accuracy %: {accuracy:3.0f}, Win %: {win_after_white:2.0f}')
                prev_evaluation = score
                if board.turn == chess.WHITE:
                    move_number += 1
            node = node.variations[0]
    return accuracies_white, accuracies_black, total_cp_loss_white, total_cp_loss_black, win_chances


def analyze_pgn(input_source, engine_path, threads, depth, is_verbose):
    (harmonic_mean_accuracy_white, weighted_mean_accuracy_white, avg_cp_loss_white, harmonic_mean_accuracy_black,
     weighted_mean_accuracy_black, avg_cp_loss_black, accuracy_white, accuracy_black) = 0, 0, 0, 0, 0, 0, 0, 0

    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    engine.configure({"Threads": threads})
    board = chess.Board()

    (accuracies_white, accuracies_black, total_cp_loss_white, total_cp_loss_black, win_chances) = (
        process(input_source, engine, depth, is_verbose, board))

    engine.quit()

    if accuracies_white and accuracies_black:
        move_count_white, move_count_black = len(accuracies_white), len(accuracies_black)
        avg_cp_loss_white = total_cp_loss_white / move_count_white
        avg_cp_loss_black = total_cp_loss_black / move_count_black
        harmonic_mean_accuracy_white = harmonic_mean(accuracies_white)
        harmonic_mean_accuracy_black = harmonic_mean(accuracies_black)
        weighted_mean_accuracy_white = volatility_weighted_mean(accuracies_white, win_chances, True)
        weighted_mean_accuracy_black = volatility_weighted_mean(accuracies_black, win_chances, False)
        accuracy_white = (harmonic_mean_accuracy_white + weighted_mean_accuracy_white) / 2
        accuracy_black = (harmonic_mean_accuracy_black + weighted_mean_accuracy_black) / 2

    if is_verbose:
        print(
            f'Harmonic White: {harmonic_mean_accuracy_white:.0f}, Weighted White: {weighted_mean_accuracy_white:.0f}, '
            f'Harmonic Black: {harmonic_mean_accuracy_black:.0f}, Weighted Black: {weighted_mean_accuracy_black:.0f}')
        print('Average centipawn loss (White), Accuracy (White), Average centipawn loss (Black), Accuracy (Black):')

    print(f'{avg_cp_loss_white:.0f}, {accuracy_white:.0f}, {avg_cp_loss_black:.0f}, {accuracy_black:.0f}')


def print_usage():
    print("Usage: python chess_accuracy.py [depth] [threads] [engine_path] [-file=path_to_pgn_file | -pgn=pgn_string] "
          "[-verbose]")
    print("Examples:")
    print("    python avg_cp_loss.py 16 2 ./stockfish -file=game.pgn")
    print("    python avg_cp_loss.py 16 2 ./stockfish -pgn=\"1.e4 e5 2.Nf3 Nc6 3.Bb5 a6\"")
    print("    cat game.pgn | python avg_cp_loss.py 16 2 ./stockfish")


if __name__ == "__main__":
    is_verbose_arg = False
    try:
        if len(sys.argv) < 4:
            print("Error: at least three arguments are required.")
            print_usage()
            sys.exit(1)

        depth_arg = int(sys.argv[1])
        threads_arg = int(sys.argv[2])
        engine_path_arg = sys.argv[3]
        data_file = sys.stdin

        for arg in sys.argv[4:]:
            if arg.startswith("-file="):
                data_file = io.open(arg.split("=", 1)[1], 'r')
            elif arg.startswith("-pgn="):
                data_file = io.StringIO(arg.split("=", 1)[1])
            elif arg == "-verbose":
                is_verbose_arg = True

        analyze_pgn(data_file, engine_path_arg, threads_arg, depth_arg, is_verbose_arg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if is_verbose_arg:
            traceback.print_exc()
        sys.exit(1)
