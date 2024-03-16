# Chess Game Accuracy Analysis Script

This script processes chess PGN (Portable Game Notation) data to compute the average centipawn loss and the harmonic mean of accuracy for both players.

## Requirements

- Python 3.6 or higher
- `chess` Python library
- Stockfish chess engine (compatible version for your system)

## Installation

1. Install Python 3.6+ from [python.org](https://www.python.org/).
2. Install the `chess` library using pip:
    ```bash
    pip install python-chess
    ```
3. Download the Stockfish engine from the official [Stockfish website](https://stockfishchess.org/download/) and place it in a known directory.

## Usage

Basic usage requires specifying the analysis depth, number of threads, and path to the Stockfish engine. You can input PGN data either from a file or directly as a string:

### From a File

```bash
python chess_accuracy.py 16 2 /path/to/stockfish -file=/path/to/game.pgn
```

### From a PGN String

```bash
python chess_accuracy.py 16 2 /path/to/stockfish -pgn="1.e4 e5 2.Nf3 Nc6 3.Bb5 a6"
```

### Using Standard Input

You can also pipe PGN data into the script:

```bash
cat /path/to/game.pgn | python chess_accuracy.py 16 2 /path/to/stockfish
```

### Verbose Output

For detailed output, including move-by-move analysis, add the `-verbose` flag at the end:

```bash
python chess_accuracy.py 16 2 /path/to/stockfish -file=/path/to/game.pgn -verbose
```

## Output

The script outputs the average centipawn loss and harmonic mean of accuracy for both players, formatted as follows:

```
Average centipawn loss (White), Accuracy harmonic mean (White), Average centipawn loss (Black), Accuracy harmonic mean (Black):
44, 84, 15, 95
```

For verbose mode, additional details for each move are printed to the console.

## License

MIT