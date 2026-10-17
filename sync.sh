#!/bin/sh
# Hourly: pull other machines' data, refresh this machine's, push.
set -e
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
git pull -q --rebase
for w in "--hours 5" "--days 1" "--days 7"; do
  python3 claude_usage.py --shared data $w
done
git add data/*.json
git diff --cached --quiet || git commit -qm "usage: $(hostname -s) $(date '+%F %H:%M')"
git push -q || { git pull -q --rebase && git push -q; }
