import chess

class ChessGame:
    """ Manages a single chess game. Keeps track of board and whose turn it is. """

    def __init__(self):
        # creates new board in standard position
        self.board = chess.Board()

    def get_state(self):
        """ Returns current state of the game, everything frontend needs to display. """
        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn else "black",
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_game_over": self.board.is_game_over(),
            "legal_moves": [move.uci() for move in self.board.legal_moves]
        } 

    def make_move(self, move_uci):
        """ Tries to make a move, in UCI format returns true if legal move, false if not legal. """
        try:
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                self.board.push(move)
                return True
            return False
        except ValueError:
            return False

    def reset(self):
        """ Resets board to starting position. """
        self.board.reset()