import io
import math
import sys
import traceback

import chess.engine
import chess.pgn


def get_eval_str(score, board):
    if score.is_mate():
        return "Mate in " + str(abs(score.relative.mate())) + " for " + (
            "White" if board.turn == chess.WHITE else "Black")
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


def process(file, engine, depth, is_verbose, board):
    accuracies_white, accuracies_black = [], []
    total_cp_loss_white, total_cp_loss_black = 0, 0
    prev_evaluation = 17
    move_number = 1

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

                win_before = winning_chances_percent(prev_evaluation)
                win_after = winning_chances_percent(score)

                if board.turn == chess.WHITE:
                    win_before, win_after = 100 - win_before, 100 - win_after

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
                    move_color = "White" if board.turn == chess.BLACK else "Black"
                    print(
                        f'{move_number}. {move_color} {san_move}, Eval: {get_eval_str(result["score"], board)}, '
                        f'Centipawn Loss: {cp_loss}, Accuracy: {accuracy:.0f}')
                prev_evaluation = score
                if board.turn == chess.WHITE:
                    move_number += 1
            node = node.variations[0]
    return accuracies_white, accuracies_black, total_cp_loss_white, total_cp_loss_black


def analyze_pgn(input_source, engine_path, threads, depth, is_verbose):
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    engine.configure({"Threads": threads})
    board = chess.Board()

    (accuracies_white, accuracies_black, total_cp_loss_white, total_cp_loss_black) = (
        process(input_source, engine, depth, is_verbose, board))

    engine.quit()

    move_count_white, move_count_black = len(accuracies_white), len(accuracies_black)

    avg_cp_loss_white = total_cp_loss_white / move_count_white if move_count_white else 0
    avg_cp_loss_black = total_cp_loss_black / move_count_black if move_count_black else 0
    accuracy_white = harmonic_mean(accuracies_white) if accuracies_white else 0
    accuracy_black = harmonic_mean(accuracies_black) if accuracies_black else 0

    if avg_cp_loss_white < avg_cp_loss_black:
        accuracy_black = min(accuracy_black, accuracy_white - 1)
    else:
        if avg_cp_loss_white > avg_cp_loss_black:
            accuracy_white = min(accuracy_white, accuracy_black - 1)

    if is_verbose:
        print('Average centipawn loss (White), Accuracy harmonic mean (White), '
              'Average centipawn loss (Black), Accuracy harmonic mean (Black):')

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
                data_file = io.open(arg.split("=")[1], 'r')
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
