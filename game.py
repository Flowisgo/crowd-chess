# game.py
# Job: "I know the state of the chess board and the rules"

import chess
import chess.engine
import random


class ChessGame:
    """
    Manages a single chess game.
    Keeps track of the board and whose turn it is.
    """

    def __init__(self, engine_path=None, think_time=1.0):
        self.board = chess.Board()
        self.engine_path = engine_path
        self.engine = None
        self.think_time = think_time

    def _ensure_engine(self):
        """Create the engine the first time it's needed."""
        if self.engine is None and self.engine_path:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            self.engine.configure({"Threads": 2})
            self.engine.configure({"Hash": 128})

    def get_state(self):
        """Return everything the frontend needs to display the game."""
        legal_uci = [move.uci() for move in self.board.legal_moves]
        legal_san = {move.uci(): self.board.san(move) for move in self.board.legal_moves}
        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_game_over": self.board.is_game_over(),
            "legal_moves": legal_uci,
            "legal_moves_san": legal_san
        }

    def is_legal(self, move_uci):
        """Check if a UCI move is legal on the current board."""
        try:
            move = chess.Move.from_uci(move_uci)
            return move in self.board.legal_moves
        except ValueError:
            return False

    def get_san(self, move_uci):
        """
        Convert a UCI move to SAN. Falls back to the UCI string if the
        move isn't legal on the current board.
        """
        try:
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                return self.board.san(move)
        except (ValueError, AssertionError):
            pass
        return move_uci

    def make_move(self, move_uci):
        """
        Try to make a move in UCI format. Returns the SAN string if the
        move was legal and was made, None otherwise.
        """
        try:
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                san = self.board.san(move)
                self.board.push(move)
                return san
            return None
        except ValueError:
            return None

    def make_random_move(self):
        """Play a random legal move. Returns the SAN, or None if game is over."""
        if self.board.is_game_over():
            return None
        move = random.choice(list(self.board.legal_moves))
        san = self.board.san(move)
        self.board.push(move)
        return san

    def make_engine_move(self):
        """
        Ask Stockfish for its best move and play it.
        Returns (uci, san) tuple, or (None, None) if the game is over.
        """
        if self.board.is_game_over():
            return None, None

        self._ensure_engine()

        if self.engine is None:
            move = random.choice(list(self.board.legal_moves))
            san = self.board.san(move)
            self.board.push(move)
            return move.uci(), san

        result = self.engine.play(
            self.board,
            chess.engine.Limit(time=self.think_time)
        )
        move = result.move
        san = self.board.san(move)
        self.board.push(move)
        return move.uci(), san

    def reset(self):
        """Reset the board to the starting position."""
        self.board = chess.Board()

    def quit(self):
        """Shut down the engine cleanly."""
        if self.engine:
            self.engine.quit()
            self.engine = None