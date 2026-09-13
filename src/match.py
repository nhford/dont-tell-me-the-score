"""Spoiler-safe title matching. Never log or return the title itself."""

from __future__ import annotations

import re

from teams import VILLA_SLUG, parse_teams

HIGHLIGHTS = re.compile(
    r"\b(?:highlights?|extended|recap)\b",
    re.IGNORECASE,
)
EXCLUDE = re.compile(
    r"""
    every\s+(?:single\s+)?goal
    | matchweek
    | press(?:\s+conference|\s+er)?
    | interview
    | training
    | behind\s+the\s+scenes
    | unseen
    | live\s+stream
    | goals?\s+of\s+the
    | fantasy
    | build-?up
    | pre-?match
    | post-?match
    | tunnel
    | academy
    | \bu21\b
    | \bu18\b
    | women
    | wsl
    | champions\s+league
    | europa
    | conference\s+league
    | fa\s+cup
    | carabao
    | efl\s+cup
    | super\s+cup
    | friendly
    | pre-?season
    """,
    re.IGNORECASE | re.VERBOSE,
)

PREFERRED_DURATION = (7 * 60, 16 * 60)
ACCEPTABLE_DURATION = (2 * 60, 20 * 60)


def is_pl_highlight(title: str) -> bool:
    if not title or EXCLUDE.search(title) or not HIGHLIGHTS.search(title):
        return False
    return parse_teams(title) is not None


def is_villa_pl_highlight(title: str) -> bool:
    teams = parse_teams(title) if is_pl_highlight(title) else None
    return bool(teams and VILLA_SLUG in teams)


def duration_rank(seconds: int | None) -> int:
    if seconds is None:
        return 2
    low, high = PREFERRED_DURATION
    if low <= seconds <= high:
        return 0
    amin, amax = ACCEPTABLE_DURATION
    if amin <= seconds <= amax:
        return 1
    return 3


def is_watchable_duration(seconds: int | None) -> bool:
    if seconds is None:
        return True
    return duration_rank(seconds) < 3
