# Don't tell me the score

Spoiler-safe Aston Villa Premier League recap watcher.

It watches official YouTube channels for a new Villa league recap, then emails a **spoiler-safe player link** with no score, no title, and no thumbnail. The email never includes a YouTube URL, so Gmail cannot preview the result.

## What you should know first

Official Premier League YouTube titles and thumbnails **do spoil the game**. Titles usually include the score. Thumbnails usually show a player or a celebration. There is no safe official thumbnail.

The 8–10 minute "standard recap" from the league channel is also not what currently gets posted for each Villa match. In practice:

- The official Premier League channel is mostly compilations, not a single-match 8–10 minute edit
- The official Aston Villa channel posts a short official league recap, typically around 3–4 minutes
- The longer ~10 minute club edit is on VillaTV (free Essential Membership), not YouTube

This watcher therefore emails the official YouTube recap when it appears, and prefers a 7–15 minute edit if the league channel posts one. It ignores press conferences, training, interviews, cup ties, and "every goal this matchweek" compilations.

## Email setup

1. Turn on 2-Step Verification for `noahford.ma@gmail.com`.
2. Create a [Gmail app password](https://myaccount.google.com/apppasswords). The normal Gmail password will not work.
3. Copy `config/local.env.example` to `config/local.env` and set `SMTP_PASSWORD` to that app password.
4. Host the spoiler-safe player on GitHub Pages (`docs/` on `main`) and set `WATCH_BASE_URL` to that site. Without it, there is no safe link to email.

The email subject is `Villa recap ready`. The body is a link to the covered player, not to YouTube. Gmail's preview crawler does not see the `#` fragment, so the inbox preview stays generic.

## GitHub Actions (cloud, recommended)

This is the reliable setup: it runs even when this computer is asleep.

1. Re-authenticate GitHub (`gh auth refresh -h github.com`) and push this repo.
2. Make the repo public if you want GitHub Pages on a free account.
3. Settings → Pages → Deploy from a branch → `main` / `/docs`.
4. Settings → Secrets → `SMTP_USER` and `SMTP_PASSWORD`.
5. Optional repository variable: `WATCH_BASE_URL=https://YOUR_USERNAME.github.io/dont-tell-me-the-score/`
6. Actions → **Villa recap watcher** → Run workflow → send a test email first, then leave the half-hour schedule on.

The first run with an empty `state/seen.json` only records recaps that already exist. It will not dump older games at you.

## Local Mac scheduler

```bash
chmod +x scripts/*.sh
./scripts/run-local.sh --seed
./scripts/run-local.sh --test-email
./scripts/install-launchd.sh
```

That checks every 30 minutes. Logs go to `state/launchd.*.log`.

## Manual commands

```bash
./scripts/run-local.sh --dry-run
./scripts/run-local.sh
```

The checker never prints titles, scores, thumbnails, or YouTube URLs.
