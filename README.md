# flight-alerts

Telegram alerts for aviation events worth looking at — emergency squawks,
diversions, unmanned aircraft, rare airframes and unusual routings.

Runs entirely on GitHub Actions. No server, no machine of your own needs to be on.
Python standard library only — no dependencies to install.

## What it sends

**🚨 Instantly** — squawk 7700 / 7600 / 7500, and diversions. Each alert carries the
aircraft, altitude, position, filed route, a rendered picture of its track, and a
button through to Flightradar24.

**📡 Roughly hourly** — a single digest of things that are interesting but not urgent:
unmanned aircraft, uncommon types, and fifth-freedom routings (an airline flying
between two countries that aren't its own).

**🌅 Daily** — a roundup: what was caught, how many aircraft were observed, and the
most common types seen.

The tiering is deliberate. Most runs find nothing, and an alert you learn to ignore is
worse than no alert at all.

## Setup

**1. Create the bot.** Message [@BotFather](https://t.me/botfather) on Telegram, send
`/newbot`, follow the prompts. It gives you a token like `1234567890:AAxxxxxxxx`.

**2. Get your chat ID.** Send your new bot any message, then open:

    https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates

Find `"chat":{"id":123456789` in the response. That number is your chat ID.

**3. Add both as repository secrets.** In this repo: *Settings → Secrets and variables
→ Actions → New repository secret*. Add:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | the number from step 2 |

The token lives only in GitHub Secrets. It is never committed and never appears in logs.

**4. Enable Actions.** Go to the Actions tab and enable workflows. Trigger a first run
by hand with *Run workflow* to check it works before leaving it to the schedule.

## Things worth knowing

**Scheduled runs are late.** GitHub runs `schedule:` workflows on a best-effort basis.
Five minutes is the minimum interval, but under load runs are commonly 5–20 minutes
late and are occasionally skipped. Emergency squawks usually persist long enough to
still be caught, but a short event can be missed. This is a GitHub limitation, not a
bug here.

**Keep the repo public.** Public repositories get unlimited Actions minutes. Private
ones get 2,000/month, and a five-minute schedule is roughly 8,600 runs — far past it.

**Data comes from [adsb.lol](https://adsb.lol)**, a free community ADS-B network with
no API key. Flightradar24 is used only for the links in the alerts.

**Every run checks the feed is alive** before reporting anything, by counting aircraft
over London. If that comes back near zero the bot says the source is unreliable rather
than implying a quiet sky — a silently dead feed is the one failure that would make
this worthless.

**State lives in `state.json`**, committed back by the workflow after each run. It
holds what's already been alerted (so you're not told twice), the accumulated route
cache, and type-frequency counts. Deleting it resets the bot.

## Rarity is measured, not guessed

There's no hand-written list of "rare" aircraft. The bot counts how often it sees every
type and flags the ones in the bottom fraction once it has enough observations. It
calibrates itself, and adjusts by region — a 737 is unremarkable over London and
notable over the South Pacific.
