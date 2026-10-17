#!/bin/bash
# Installs the hourly sync on this Mac. Run inside the cloned repo:
#   gh repo clone S0LLARU/claude-usage ~/.claude/usage-tracker && bash ~/.claude/usage-tracker/install.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.user.claude-usage"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

gh auth setup-git
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string><string>-c</string>
    <string>/bin/sh "$REPO/sync.sh" &gt; "$REPO/last_run.log" 2&gt;&amp;1</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
PL

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. Runs every hour. Report: $REPO/data/report_5.0h.txt  Log: $REPO/last_run.log"
