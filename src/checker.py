#!/usr/bin/env python3
"""Catalog PL recaps and email a spoiler-safe Villa player link.

Never prints titles, thumbnails, scores, or YouTube URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from match import duration_rank, is_pl_highlight, is_watchable_duration
from teams import VILLA_SLUG, frontend_teams, parse_teams

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "seen.json"
RECAPS_PATH = ROOT / "docs" / "recaps.json"
TEAMS_PATH = ROOT / "docs" / "teams.json"
ATOM = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

# Official club channels only. Sky Sports highlights are UK-blocked and
# cannot play in the embedded player for viewers outside Britain.
CHANNELS = (
    ("arsenal", "UCpryVRk_VDudG8SHXgWcG0w"),
    ("aston-villa", "UCICNP0mvtr0prFwGUQIABfQ"),
    ("brighton", "UC2YbrhnGREhyB8DwXOEO99Q"),
    ("chelsea", "UCU2PacFf99vhb3hNiYDmxww"),
    ("everton", "UCtK4QAczAN2mt2ow_jlGinQ"),
    ("man-united", "UC6yW44UGJJBvYTlfC7CRg2Q"),
    ("sunderland", "UCrw-7k6yJc0EMJdf-0BAkoQ"),
    ("tottenham", "UCEg25rdRZXg32iwai6N6l0w"),
)

WINDOW_DAYS = 5
COOLDOWN = timedelta(hours=36)
USER_AGENT = "dont-tell-me-the-score/1.0 (spoiler-safe recap watcher)"
LENGTH_RE = re.compile(r'"lengthSeconds":"(\d+)"')


@dataclass(frozen=True)
class Video:
    video_id: str
    published: datetime
    channel: str
    home: str | None = None
    away: str | None = None
    duration: int | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def today_utc() -> date:
    return utcnow().date()


def window_start(now: date | None = None) -> date:
    return (now or today_utc()) - timedelta(days=WINDOW_DAYS - 1)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"seen_ids": [], "last_notified_at": None}
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def load_recaps() -> list[dict]:
    if not RECAPS_PATH.exists():
        return []
    try:
        payload = json.loads(RECAPS_PATH.read_text())
    except json.JSONDecodeError:
        return []
    return list(payload.get("recaps") or [])


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_published(raw: str) -> datetime:
    raw = raw.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def fetch_channel_videos(channel_name: str, channel_id: str) -> list[Video]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    root = ET.fromstring(http_get(url))
    videos: list[Video] = []
    for entry in root.findall("atom:entry", ATOM):
        title = entry.findtext("atom:title", default="", namespaces=ATOM) or ""
        if not is_pl_highlight(title):
            continue
        teams = parse_teams(title)
        if not teams:
            continue
        video_id = entry.findtext("yt:videoId", default="", namespaces=ATOM) or ""
        published_raw = entry.findtext("atom:published", default="", namespaces=ATOM) or ""
        if not video_id or not published_raw:
            continue
        videos.append(
            Video(
                video_id=video_id,
                published=parse_published(published_raw),
                channel=channel_name,
                home=teams[0],
                away=teams[1],
            )
        )
    return videos


def fetch_duration(video_id: str) -> int | None:
    try:
        html = http_get(f"https://www.youtube.com/watch?v={video_id}").decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    match = LENGTH_RE.search(html)
    return int(match.group(1)) if match else None


def pick_video(candidates: list[Video]) -> Video | None:
    watchable = [v for v in candidates if is_watchable_duration(v.duration)]
    if not watchable:
        return None
    return sorted(watchable, key=lambda v: (duration_rank(v.duration), -v.published.timestamp()))[0]


def match_key(item: dict | Video) -> tuple[str, frozenset[str]]:
    if isinstance(item, Video):
        day = item.published.date().isoformat()
        return day, frozenset({item.home or "", item.away or ""})
    return item["date"], frozenset({item["home"], item["away"]})


def recap_record(video: Video) -> dict:
    return {
        "date": video.published.date().isoformat(),
        "home": video.home,
        "away": video.away,
        "video_id": video.video_id,
    }


def write_catalog(videos: list[Video], start: date) -> int:
    grouped: dict[tuple[str, frozenset[str]], list[Video]] = {}
    for video in videos:
        if not video.home or not video.away or video.published.date() < start:
            continue
        grouped.setdefault(match_key(video), []).append(video)

    chosen: dict[tuple[str, frozenset[str]], dict] = {}
    for key, candidates in grouped.items():
        winner = candidates[0]
        if len(candidates) > 1:
            scored = [
                replace(video, duration=video.duration if video.duration is not None else fetch_duration(video.video_id))
                for video in candidates
            ]
            winner = pick_video(scored) or winner
        chosen[key] = recap_record(winner)

    recaps = sorted(chosen.values(), key=lambda r: (r["date"], r["home"], r["away"]), reverse=True)
    RECAPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECAPS_PATH.write_text(json.dumps({"updated": utcnow().isoformat(), "recaps": recaps}, indent=2) + "\n")
    TEAMS_PATH.write_text(json.dumps(frontend_teams(), indent=2) + "\n")
    return len(recaps)


def watch_base_url() -> str:
    base = os.environ.get("WATCH_BASE_URL", "").strip()
    if not base:
        raise SystemExit("WATCH_BASE_URL is not set")
    return base.rstrip("/")


def watch_url(video_id: str) -> str:
    return f"{watch_base_url()}/#{video_id}"


def send_email(subject: str, body: str) -> None:
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if not user or not password:
        raise SystemExit("SMTP_USER and SMTP_PASSWORD must be set")
    to_addr = os.environ.get("EMAIL_TO", "noahford.ma@gmail.com").strip()
    from_addr = os.environ.get("EMAIL_FROM", user).strip()
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        smtp.send_message(message)


def notify(video_id: str) -> None:
    send_email(
        subject="Villa recap ready",
        body=(
            "Aston Villa Premier League recap is ready.\n"
            "This email has no score and no thumbnail.\n"
            "Open this spoiler-safe player:\n"
            f"{watch_url(video_id)}\n"
        ),
    )


def notify_test() -> None:
    send_email(
        subject="Villa recap watcher test",
        body=(
            "Test email only. Future alerts will say the recap is ready "
            "and include a spoiler-safe player link.\n"
            f"{watch_base_url()}/\n"
        ),
    )


def in_cooldown(state: dict, now: datetime) -> bool:
    raw = state.get("last_notified_at")
    if not raw:
        return False
    last = datetime.fromisoformat(raw)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return now - last < COOLDOWN


def collect_videos() -> list[Video]:
    found: list[Video] = []
    for channel_name, channel_id in CHANNELS:
        try:
            found.extend(fetch_channel_videos(channel_name, channel_id))
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
            print(f"channel-check-failed:{channel_name}:{type(exc).__name__}", file=sys.stderr)
    return found


def run(seed: bool = False, dry_run: bool = False) -> int:
    state = load_state()
    seen = set(state.get("seen_ids") or [])
    found = collect_videos()
    if not dry_run:
        count = write_catalog(found, window_start())
        print(f"cataloged {count} recap(s)")

    villa_videos = [v for v in found if VILLA_SLUG in {v.home, v.away}]

    if seed or not seen:
        for video in villa_videos:
            seen.add(video.video_id)
        state["seen_ids"] = sorted(seen)
        if not dry_run:
            save_state(state)
        print(f"seeded {len(villa_videos)} villa recap(s); future runs email only for new villa uploads")
        return 0

    new_villa = [
        replace(video, duration=fetch_duration(video.video_id))
        for video in villa_videos
        if video.video_id not in seen
    ]
    if not new_villa:
        print("no new villa recap")
        return 0

    def mark_seen() -> None:
        for video in new_villa:
            seen.add(video.video_id)
        state["seen_ids"] = sorted(seen)

    chosen = pick_video(new_villa)
    if chosen is None:
        if not dry_run:
            mark_seen()
            save_state(state)
        print("new upload(s) found but none were a watchable recap length")
        return 0

    now = utcnow()
    if in_cooldown(state, now):
        if not dry_run:
            mark_seen()
            save_state(state)
        print("new recap found but still in same-match cooldown")
        return 0

    if dry_run:
        print("dry-run: would email one spoiler-safe villa recap")
        return 0

    notify(chosen.video_id)
    mark_seen()
    state["last_notified_at"] = now.isoformat()
    save_state(state)
    print("emailed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Spoiler-safe PL recap watcher")
    parser.add_argument("--seed", action="store_true", help="Record current Villa recaps without emailing")
    parser.add_argument("--dry-run", action="store_true", help="Do not write state or send email")
    parser.add_argument("--test-email", action="store_true", help="Send a dummy spoiler-safe email")
    args = parser.parse_args()
    if args.test_email:
        notify_test()
        print("sent test email")
        return 0
    return run(seed=args.seed, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
