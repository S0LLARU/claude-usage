#!/bin/bash
# Hourly Claude Code usage tracker. Each machine publishes to its own secret gist
# (under whatever GitHub account is logged in to gh there) and reads the others'.
#
#   first machine:   bash install.sh
#   other machines:  curl -fsSL https://gist.githubusercontent.com/<link>/raw/install.sh | bash -s <link>
#   add a peer:      bash ~/.claude/usage-tracker/install.sh <peer link>
#   dashboard:       open ~/.claude/usage-tracker/data/dashboard.html
set -euo pipefail

PEER="${1:-}"
PEER="${PEER#https://gist.github.com/}"
DIR="$HOME/.claude/usage-tracker"
LABEL="com.user.claude-usage"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$DIR/data" "$HOME/Library/LaunchAgents"

# code: from the folder this script sits in, or from the peer's gist
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo)"
for f in claude_usage.py sync.sh install.sh dashboard_template.html; do
  if [ -f "$SELF_DIR/$f" ] && [ "$SELF_DIR" != "$DIR" ]; then cp "$SELF_DIR/$f" "$DIR/$f"
  elif [ ! -f "$DIR/$f" ] && [ -n "$PEER" ]; then curl -fsSL "https://gist.githubusercontent.com/$PEER/raw/$f" -o "$DIR/$f"
  fi
done

touch "$DIR/config"
. "$DIR/config"
if [ -z "${MY_GIST:-}" ]; then
  python3 "$DIR/claude_usage.py" collect
  url=$(gh gist create -d "Claude usage: $(hostname -s)" "$DIR/data/usage.json" "$DIR/claude_usage.py" "$DIR/sync.sh" "$DIR/install.sh" "$DIR/dashboard_template.html" | tail -1)
  MY_GIST="${url##*/}"
  MY_LINK="$(gh api user -q .login)/$MY_GIST"
  PEERS=""
fi
if [ -n "$PEER" ] && [[ " ${PEERS:-} " != *" $PEER "* ]]; then PEERS="${PEERS:+$PEERS }$PEER"; fi
printf 'MY_GIST=%s\nMY_LINK=%s\nPEERS="%s"\n' "$MY_GIST" "$MY_LINK" "${PEERS:-}" > "$DIR/config"

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string><string>-c</string>
    <string>/bin/sh "$DIR/sync.sh" &gt; "$DIR/last_run.log" 2&gt;&amp;1</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "Installed, runs hourly. Report: $DIR/data/report.txt"
echo "This machine's link: $MY_LINK"
echo "Peers: ${PEERS:-none}"
