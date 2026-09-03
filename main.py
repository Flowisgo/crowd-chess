# main.py
# handles http requests and responses and defines routes

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from game import ChessGame
from voting import VoteManager

app = FastAPI()

# files from 'static' folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# creates shared game instance for all users to play together
game = ChessGame()
vote_manager = VoteManager(voting_seconds = 30)

def get_voter_id(request: Request) -> str:
    """
    Gets a unique identifier for the voter based on their IP address.
    Uses client's IP address
    """
    # request.client.host contains IP address of person connecting
    return request.client.host

@app.get("/")
def home():
    """ Serve the main HTML page. """
    return FileResponse("static/index.html")

@app.get("/game")
def get_game():
    """ Returns current game state. """
    return {
        "game": game.get_state(),
        "voting": vote_manager.get_status()
    }
@app.post("/vote")
def submit_vote(move: str, request: Request):
    """ Receives a vote for a move. Move should be in UCI format.
    Each IP address gets one vote, but can be changed during voting window"""
    voter_id = get_voter_id(request)
    # record the vode
    recorded = vote_manager.record_vote(voter_id, move)
    if not recorded:
        return {
            "success": False,
            "message": "Voting has ended",
            "game": game.get_state(),
            "voting": vote_manager.get_status()
        }
    
    return {
        "success": True,
        "message": f"Voted for {move}",
        "voting": vote_manager.get_status()
    }

@app.get("/voting_status")
def voting_status():
    """ Get current voting status without game state"""
    return vote_manager.get_status()

@app.post("/check-winner")
def check_winner():
    """
    Checks if voting is over and winner should be declared.
    If voting is over and there is a winner, move is played automatically
    """
    winner_data = vote_manager.get_winner()

    if winner_data is None:
        return {
            "voting_active": True,
            "voting": vote_manager.get_status()
        }

    # Voting is over, play winning move
    if winner_data["winner"] is not None:
        game.make_move(winner_data["winner"])

    # Reset voting for the next round
    vote_manager.reset() 

    return {
        "voting_active": False,
        "winner": winner_data,
        "game": game.get_state(),
        "voting": vote_manager.get_status()
    }

@app.post("/reset")
def reset_game():
    """ Resets game to starting position and voting for next move """
    game.reset()
    vote_manager.reset()
    return {
        "message": "Game reset",
        "game": game.get_state(),
        "voting": vote_manager.get_status()
    }