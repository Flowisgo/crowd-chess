# main.py
# Job: "I define routes and handle HTTP requests/responses"

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
from game import ChessGame
from voting import VoteManager
import os
import time
import threading

app = FastAPI()

# Trust proxy headers (Railway, Render, Fly.io all use reverse proxies).
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.mount("/static", StaticFiles(directory="static"), name="static")

STOCKFISH_PATH = os.environ.get(
    "STOCKFISH_PATH",
    r"C:\Users\User\stockfish-windows-x86-64-universal\stockfish\stockfish-windows-x86-64-universal.exe"
)

game = ChessGame(engine_path=STOCKFISH_PATH)
vote_manager = VoteManager(voting_seconds=15, min_seconds=5)

_round_phase = "voting"
_game_over_at = 0.0
GAME_OVER_DELAY = 8
round_lock = threading.Lock()

# ── Viewer tracking ────────────────────────────────
_viewers = {}
VIEWER_WINDOW = 15

# ── Surrender votes ────────────────────────────────
_surrender_votes = set()


def get_client_ip(request: Request) -> str:
    """
    Get the real client IP, accounting for reverse proxies.
    X-Forwarded-For looks like: client, proxy1, proxy2
    The first entry is the original client.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def _touch_viewer(ip):
    _viewers[ip] = time.time()


def _viewer_count():
    now = time.time()
    stale = [ip for ip, t in _viewers.items() if now - t > VIEWER_WINDOW]
    for ip in stale:
        del _viewers[ip]
    return len(_viewers)


def _prune_surrender_votes():
    global _surrender_votes
    _surrender_votes = {ip for ip in _surrender_votes if ip in _viewers}


def _surrender_needed():
    vc = max(1, _viewer_count())
    return vc // 2 + 1


def _maybe_finish_game_over():
    """Auto-reset the game a few seconds after it ends."""
    global _round_phase
    if _round_phase == "game_over" and time.time() - _game_over_at >= GAME_OVER_DELAY:
        game.reset()
        vote_manager.reset()
        _surrender_votes.clear()
        _round_phase = "voting"


def get_voter_id(request: Request) -> str:
    return get_client_ip(request)


def voting_status_with_san():
    _maybe_finish_game_over()

    vote_manager.set_viewer_count(_viewer_count())
    status = vote_manager.get_status()
    raw_tally = status.pop("current_tally", {})
    status["tally"] = [
        {"uci": uci, "san": game.get_san(uci), "count": count}
        for uci, count in sorted(raw_tally.items(), key=lambda x: -x[1])
    ]
    status["viewer_count"] = _viewer_count()
    status["phase"] = _round_phase

    if _round_phase == "game_over":
        remaining = max(0, GAME_OVER_DELAY - (time.time() - _game_over_at))
        status["game_over_seconds"] = int(remaining + 0.999)
    else:
        status["game_over_seconds"] = None

    _prune_surrender_votes()
    status["surrender_votes"] = len(_surrender_votes)
    status["surrender_needed"] = _surrender_needed()
    return status


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/game")
def get_game(request: Request):
    _touch_viewer(get_client_ip(request))
    return {
        "game": game.get_state(),
        "voting": voting_status_with_san()
    }


@app.post("/vote")
def submit_vote(move: str, request: Request):
    _touch_viewer(get_client_ip(request))
    vote_manager.set_viewer_count(_viewer_count())

    if _round_phase != "voting":
        return {
            "success": False,
            "message": "Round in progress",
            "voting": voting_status_with_san()
        }

    if not game.is_legal(move):
        return {
            "success": False,
            "message": "Illegal move",
            "voting": voting_status_with_san()
        }

    voter_id = get_voter_id(request)
    recorded = vote_manager.record_vote(voter_id, move)

    if not recorded:
        return {
            "success": False,
            "message": "Voting has ended",
            "voting": voting_status_with_san()
        }

    san = game.get_san(move)
    return {
        "success": True,
        "message": f"Voted for {san}",
        "move_san": san,
        "voting": voting_status_with_san()
    }


@app.get("/voting-status")
def voting_status(request: Request):
    _touch_viewer(get_client_ip(request))
    return voting_status_with_san()


@app.post("/check-winner")
def check_winner(request: Request):
    global _round_phase
    _touch_viewer(get_client_ip(request))
    vote_manager.set_viewer_count(_viewer_count())

    with round_lock:
        if _round_phase != "voting":
            return {
                "phase": _round_phase,
                "game": game.get_state(),
                "voting": voting_status_with_san()
            }

        if vote_manager.is_voting_open():
            return {
                "phase": "voting",
                "voting_active": True,
                "voting": voting_status_with_san()
            }

        winner_data = vote_manager.get_winner()

        # Capture SAN BEFORE the board moves, then clear the vote manager
        # so the returned status has no stale UCI tally in it.
        winning_uci = winner_data["winner"] if winner_data else None
        winning_san = game.get_san(winning_uci) if winning_uci else None

        vote_manager.reset()

        if winning_uci:
            game.make_move(winning_uci)
        else:
            winning_san = game.make_random_move()

        _round_phase = "engine_thinking"

        return {
            "phase": "engine_thinking",
            "voting_active": False,
            "winner": {
                **(winner_data or {"winner": None, "total_votes": 0, "tied": False}),
                "winner_san": winning_san
            },
            "game": game.get_state(),
            "voting": voting_status_with_san()
        }


@app.post("/engine-move")
def engine_move(request: Request):
    global _round_phase, _game_over_at
    _touch_viewer(get_client_ip(request))

    with round_lock:
        if _round_phase != "engine_thinking":
            return {
                "phase": _round_phase,
                "game": game.get_state(),
                "voting": voting_status_with_san()
            }

        engine_uci, engine_san = game.make_engine_move()

        vote_manager.reset()

        if game.get_state()["is_game_over"]:
            _round_phase = "game_over"
            _game_over_at = time.time()
        else:
            _round_phase = "voting"

        return {
            "phase": _round_phase,
            "engine_move": engine_uci,
            "engine_move_san": engine_san,
            "game": game.get_state(),
            "voting": voting_status_with_san()
        }


@app.post("/surrender")
def surrender(request: Request, active: bool = True):
    global _round_phase
    _touch_viewer(get_client_ip(request))

    ip = get_client_ip(request)
    if active:
        _surrender_votes.add(ip)
    else:
        _surrender_votes.discard(ip)

    _prune_surrender_votes()
    needed = _surrender_needed()

    if active and len(_surrender_votes) >= needed:
        with round_lock:
            game.reset()
            vote_manager.reset()
            _surrender_votes.clear()
            _round_phase = "voting"

        return {
            "reset": True,
            "message": "Game reset by surrender vote",
            "game": game.get_state(),
            "voting": voting_status_with_san()
        }

    return {
        "reset": False,
        "message": "Surrender vote recorded",
        "game": game.get_state(),
        "voting": voting_status_with_san()
    }


@app.post("/reset")
def reset_game(request: Request):
    global _round_phase
    _touch_viewer(get_client_ip(request))

    with round_lock:
        game.reset()
        vote_manager.reset()
        _round_phase = "voting"
        _surrender_votes.clear()

    return {
        "message": "Game reset",
        "game": game.get_state(),
        "voting": voting_status_with_san()
    }