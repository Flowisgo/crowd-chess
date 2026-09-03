# voting.py
# collects votes and counts winner

import time
import random
from collections import Counter

class VoteManager:
    """ Manages voting for single move, tracks who voted for what and picks winner. """

    def __init__(self, voting_seconds=30):
        # length of voting period
        self.voting_seconds = voting_seconds

        # Dictionary mapping ip adress to vote (move_uci)
        self.votes = {}

        # When the current voting period started
        self.voting_started_at = time.time()

    def record_vote(self, voter_id, move_uci):
        """
        Records vote from a specific voter.
        Only latest vote from each user counts.
        Returns true if vote counted, false if voting ended
        """
        if self.is_voting_open():
            self.votes[voter_id] = move_uci
            return True
        return False

    def get_time_remaining(self):
        """ Returns how much time is left in this voting period"""
        elapsed = time.time() - self.voting_started_at
        remaining = self.voting_seconds - elapsed
        return max(0, int(remaining))

    def is_voting_open(self):
        """ Returns true if voting period is still open, false if not"""
        return self.get_time_remaining() > 0

    def get_winner(self):
        """
        Counts votes and returns winning move
        If voting isn't over yet, returns None.
        If tie, pick randomly.
        Returns dictionary with winner and vote counts
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

        # Count votes
        move_counts = Counter(self.votes.values())

        # Find highest vote count
        max_votes = max(move_counts.values())

        # Get all moves tied for most votes
        tied_winners = [move for move, count in move_counts.items() if count == max_votes]

        # Pick randomly if tie
        winner = random.choice(tied_winners)

        return {
            "winner": winner,
            "vote_counts": dict(move_counts),
            "total_votes": len(self.votes),
            "tied": len(tied_winners) > 1,
            "message": f"Winning move: {winner} with {max_votes} votes"
        }

    def reset(self):
        """ Resets voting for next move """
        self.votes = {}
        self.voting_started_at = time.time()

    def get_status(self):
        """ Returns current voting status"""
        return {
            "votes_so_far": len(self.votes),
            "time_remaining": self.get_time_remaining(),
            "voting_open": self.is_voting_open(),
            "current_tally": dict(Counter(self.votes.values()))
        }