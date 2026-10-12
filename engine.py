# engine.py
# talks to Stockfish and return the best move for a position

import chess
import chess.engine


class ChessEngine:
    """
    Wraps Stockfish so the rest of the app doesn't need to know
    anything about UCI, subprocesses, or engine configuration.
    """

    def __init__(self, engine_path, think_time=0.5):
        """
        engine_path: full path to the Stockfish .exe
        think_time: how long the engine thinks per move, in seconds.
                    0.5 is enough for strong play but snappy responses.
        """
        self.engine_path = engine_path
        self.think_time = think_time

        # Start the engine as a subprocess.
        # python-chess handles all the UCI handshake automatically.
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

        # Optional: configure engine resources.
        # Threads = how many CPU cores the engine uses.
        # Hash = how much memory (in MB) for its position cache.
        self.engine.configure({"Threads": 2})
        self.engine.configure({"Hash": 128})

    def get_best_move(self, board):
        """
        Given a chess.Board position, return Stockfish's best move
        as a UCI string like 'e7e5'.
        """
        # 'Limit(time=...)' tells the engine to think for that many seconds.
        # This keeps responses fast while still playing strong moves.
        result = self.engine.play(
            board,
            chess.engine.Limit(time=self.think_time)
        )
        return result.move.uci()

    def quit(self):
        """Shut down the engine cleanly. Call this when the server exits."""
        self.engine.quit()