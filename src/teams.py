"""Premier League team aliases and score-free title parsing."""

from __future__ import annotations

import re

# Longest aliases first at lookup time. Do not store scores here.
TEAMS: dict[str, dict] = {
    "arsenal": {
        "name": "Arsenal",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t3.png",
        "aliases": ("arsenal", "gunners"),
    },
    "aston-villa": {
        "name": "Aston Villa",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t7.png",
        "aliases": ("aston villa", "avfc", "villa"),
    },
    "bournemouth": {
        "name": "AFC Bournemouth",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t91.png",
        "aliases": ("bournemouth", "afcb", "cherries"),
    },
    "brentford": {
        "name": "Brentford",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t94.png",
        "aliases": ("brentford", "bees"),
    },
    "brighton": {
        "name": "Brighton",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t36.png",
        "aliases": ("brighton and hove", "brighton & hove", "brighton", "seagulls", "bhafc"),
    },
    "chelsea": {
        "name": "Chelsea",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t8.png",
        "aliases": ("chelsea", "cfc"),
    },
    "coventry": {
        "name": "Coventry City",
        "logo": "https://resources.premierleague.com/premierleague25/badges-alt/9.svg",
        "aliases": ("coventry city", "coventry", "sky blues"),
    },
    "crystal-palace": {
        "name": "Crystal Palace",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t31.png",
        "aliases": ("crystal palace", "palace", "cpfc"),
    },
    "everton": {
        "name": "Everton",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t11.png",
        "aliases": ("everton", "toffees"),
    },
    "fulham": {
        "name": "Fulham",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t54.png",
        "aliases": ("fulham", "cottagers"),
    },
    "hull": {
        "name": "Hull City",
        "logo": "https://resources.premierleague.com/premierleague25/badges-alt/41.svg",
        "aliases": ("hull city", "hull", "tigers"),
    },
    "ipswich": {
        "name": "Ipswich Town",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t40.png",
        "aliases": ("ipswich town", "ipswich", "tractor boys"),
    },
    "leeds": {
        "name": "Leeds United",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t2.png",
        "aliases": ("leeds united", "leeds", "lufc"),
    },
    "liverpool": {
        "name": "Liverpool",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t14.png",
        "aliases": ("liverpool", "lfc"),
    },
    "man-city": {
        "name": "Manchester City",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t43.png",
        "aliases": ("manchester city", "man city", "mcfc"),
    },
    "man-united": {
        "name": "Manchester United",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t1.png",
        "aliases": ("manchester united", "man united", "man utd", "mufc"),
    },
    "newcastle": {
        "name": "Newcastle United",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t4.png",
        "aliases": ("newcastle united", "newcastle", "nufc", "magpies"),
    },
    "nottingham-forest": {
        "name": "Nottingham Forest",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t17.png",
        "aliases": ("nottingham forest", "nottm forest", "notts forest", "forest", "nffc"),
    },
    "sunderland": {
        "name": "Sunderland",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t56.png",
        "aliases": ("sunderland", "safc", "black cats"),
    },
    "tottenham": {
        "name": "Tottenham",
        "logo": "https://resources.premierleague.com/premierleague/badges/50/t6.png",
        "aliases": ("tottenham hotspur", "tottenham", "spurs", "thfc"),
    },
}

VILLA_SLUG = "aston-villa"
SCORE = re.compile(r"\d+\s*[-–]\s*\d+")
NOISE = re.compile(
    r"\b(?:highlights?|extended|recap|premier\s+league|\bpl\b|epl|vs\.?|v)\b",
    re.IGNORECASE,
)


def _alias_table() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for slug, meta in TEAMS.items():
        for alias in meta["aliases"]:
            pairs.append((alias.lower(), slug))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


ALIASES = _alias_table()


def frontend_teams() -> dict[str, dict[str, str]]:
    return {slug: {"name": meta["name"], "logo": meta["logo"]} for slug, meta in TEAMS.items()}


def parse_teams(title: str) -> tuple[str, str] | None:
    if not title:
        return None
    text = title.lower().replace("|", " ")
    text = SCORE.sub(" ", text)
    text = NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9& ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    found: list[str] = []
    i = 0
    while i < len(text) and len(found) < 2:
        hit = None
        for alias, slug in ALIASES:
            end = i + len(alias)
            if text[i:end] != alias:
                continue
            before = i == 0 or not text[i - 1].isalnum()
            after = end >= len(text) or not text[end].isalnum()
            if before and after:
                hit = (slug, end)
                break
        if hit:
            slug, end = hit
            if slug not in found:
                found.append(slug)
            i = end
        else:
            i += 1
    if len(found) == 2:
        return found[0], found[1]
    return None
