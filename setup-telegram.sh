#!/usr/bin/env bash
# Wires the Telegram bot into GitHub Secrets.
# Prompts for the token, never echoes it, never writes it to disk or history.
set -uo pipefail

REPO="guspzanetti/flight-alerts"

printf "Bot token (from BotFather, input hidden): "
stty -echo 2>/dev/null
read -r T
stty echo 2>/dev/null
printf "\n"

if [ -z "${T:-}" ]; then
  echo "No token entered. Aborting."; exit 1
fi

echo "→ checking the token..."
ME=$(curl -s --max-time 15 "https://api.telegram.org/bot$T/getMe")
if ! echo "$ME" | grep -q '"ok":true'; then
  echo "❌ Telegram rejected that token."
  echo "   If you ran /revoke, make sure you copied the NEW token."
  unset T; exit 1
fi
BOTNAME=$(echo "$ME" | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['username'])" 2>/dev/null)
echo "   ✅ token valid — bot is @$BOTNAME"

echo "→ looking for your chat id..."
CID=$(curl -s --max-time 15 "https://api.telegram.org/bot$T/getUpdates" \
  | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin).get('result', [])
except Exception:
    r = []
ids = [u['message']['chat']['id'] for u in r if 'message' in u]
print(ids[-1] if ids else '')
" 2>/dev/null)

if [ -z "$CID" ]; then
  echo "❌ No messages found."
  echo "   Open https://t.me/$BOTNAME, press START, send it any message, then re-run this."
  unset T; exit 1
fi
echo "   ✅ chat id: $CID"

echo "→ saving both secrets to $REPO..."
export GH_TOKEN=$(gh auth token --user guspzanetti 2>/dev/null)
if [ -z "${GH_TOKEN:-}" ]; then
  echo "❌ Could not get a GitHub token for the guspzanetti account."; unset T; exit 1
fi

gh secret set TELEGRAM_BOT_TOKEN --repo "$REPO" --body "$T"  || { echo "❌ failed"; unset T; exit 1; }
gh secret set TELEGRAM_CHAT_ID  --repo "$REPO" --body "$CID" || { echo "❌ failed"; unset T; exit 1; }
unset T

echo
echo "✅ Done. Secrets now set:"
gh secret list --repo "$REPO"
echo
echo "Tell Claude \"done\" and it will restart the run so the job picks them up."
