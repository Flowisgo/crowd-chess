# voting.py
# collects votes and counts winner

import time
import random
from collections import Counter


class VoteManager:
    """
    Manages voting for a single move, tracks who voted for what and picks winner.

    Adaptive timing: a round closes at voting_seconds, OR earlier if every
    currently active viewer has voted — but never before min_seconds.
    """

    def __init__(self, voting_seconds=30, min_seconds=5):
        self.voting_seconds = voting_seconds
        self.min_seconds = min_seconds
        self.votes = {}
        self.voting_started_at = time.time()
        self._viewer_count = 0

    def set_viewer_count(self, n):
        """main.py tells us how many viewers are currently active."""
        self._viewer_count = n

    def get_elapsed(self):
        return time.time() - self.voting_started_at

    def get_time_remaining(self):
        """Seconds left. 0 means voting is over."""
        remaining = self.voting_seconds - self.get_elapsed()
        return max(0, remaining)

    def is_voting_open(self):
        """Can votes still be cast?"""
        elapsed = self.get_elapsed()

        # Hard cap: time's up.
        if elapsed >= self.voting_seconds:
            return False

        # Floor: too early to close, even if everyone voted.
        if elapsed < self.min_seconds:
            return True

        # Early close: everyone currently watching has voted.
        if self._viewer_count > 0 and len(self.votes) >= self._viewer_count:
            return False

        return True

    def close_reason(self):
        """Why is voting closed? None if it's still open."""
        if self.is_voting_open():
            return None
        if self.get_elapsed() >= self.voting_seconds:
            return "time"
        return "everyone_voted"

    def record_vote(self, voter_id, move_uci):
        """
        Records vote from a specific voter.
        Only latest vote from each user counts.
        Returns true if vote counted, false if voting ended.
        """
        if self.is_voting_open():
            self.votes[voter_id] = move_uci
            return True
        return False

    def get_winner(self):
        """
        Counts votes and returns winning move.
        If voting isn't over yet, returns None.
        If tie, pick randomly.
        Returns dictionary with winner and vote counts.
        """
        if self.is_voting_open():
            return None

        if not self.votes:
            return {
                "winner": None,
                "vote_counts": {},
                "total_votes": 0,
                "message": "No votes were cast"
            }

        move_counts = Counter(self.votes.values())
        max_votes = max(move_counts.values())
        tied_winners = [move for move, count in move_counts.items() if count == max_votes]
        winner = random.choice(tied_winners)

        return {
            "winner": winner,
            "vote_counts": dict(move_counts),
            "total_votes": len(self.votes),
            "tied": len(tied_winners) > 1,
            "message": f"Winning move: {winner} with {max_votes} votes"
        }

    def reset(self):
        """Resets voting for next move."""
        self.votes = {}
        self.voting_started_at = time.time()

    def get_status(self):
        """Returns current voting status."""
        return {
            "votes_so_far": len(self.votes),
            "time_remaining": int(self.get_time_remaining()),
            "voting_open": self.is_voting_open(),
            "voting_seconds": self.voting_seconds,
            "close_reason": self.close_reason(),
            "current_tally": dict(Counter(self.votes.values()))
        }