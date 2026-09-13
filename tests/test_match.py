import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from checker import pick_video, Video, watch_url
from match import duration_rank, is_pl_highlight, is_villa_pl_highlight
from teams import parse_teams
from datetime import datetime, timezone


def ts(day: int) -> datetime:
    return datetime(2026, 9, day, 18, 0, tzinfo=timezone.utc)


class MatchTests(unittest.TestCase):
    def test_accepts_club_and_league_recap_titles(self):
        self.assertTrue(
            is_villa_pl_highlight("Fulham vs Aston Villa | Premier League Highlights")
        )
        self.assertTrue(
            is_villa_pl_highlight("Aston Villa vs Fulham | Premier League Highlights")
        )
        self.assertTrue(is_villa_pl_highlight("AVFC vs Fulham | PL Highlights"))
        self.assertTrue(is_pl_highlight("Arsenal vs Chelsea | Premier League Highlights"))

    def test_parses_two_teams_and_strips_scores(self):
        self.assertEqual(parse_teams("Arsenal 1-0 Chelsea | Premier League Highlights"), ("arsenal", "chelsea"))
        self.assertEqual(parse_teams("Spurs vs Man City | Highlights"), ("tottenham", "man-city"))
        self.assertIsNone(parse_teams("Arsenal press conference"))

    def test_rejects_compilations_and_non_league_videos(self):
        self.assertFalse(is_villa_pl_highlight("EVERY SINGLE GOAL from Matchweek 12"))
        self.assertFalse(is_villa_pl_highlight("Aston Villa press conference"))
        self.assertFalse(is_villa_pl_highlight("Aston Villa training"))
        self.assertFalse(is_villa_pl_highlight("Aston Villa vs Fulham | FA Cup Highlights"))
        self.assertFalse(is_villa_pl_highlight("Aston Villa Women | Premier League Highlights"))
        self.assertFalse(is_pl_highlight("Unrelated club vs Dummy Town | Premier League Highlights"))

    def test_prefers_extended_length_over_short_club_edit(self):
        short = Video("shortid12345", ts(5), "aston-villa", duration=180)
        extended = Video("longid123456", ts(5), "premier-league", duration=540)
        chosen = pick_video([short, extended])
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.video_id, "longid123456")
        self.assertEqual(duration_rank(540), 0)
        self.assertEqual(duration_rank(180), 1)

    def test_watch_url_is_player_hash_not_youtube(self):
        previous = os.environ.get("WATCH_BASE_URL")
        os.environ["WATCH_BASE_URL"] = "https://example.github.io/dont-tell-me-the-score/"
        try:
            url = watch_url("abcdefghijk")
            self.assertEqual(url, "https://example.github.io/dont-tell-me-the-score/#abcdefghijk")
            self.assertNotIn("youtube.com", url)
            self.assertNotIn("youtu.be", url)
        finally:
            if previous is None:
                os.environ.pop("WATCH_BASE_URL", None)
            else:
                os.environ["WATCH_BASE_URL"] = previous


if __name__ == "__main__":
    unittest.main()
