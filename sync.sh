#!/bin/sh
# Hourly: publish this machine's usage to its secret gist, fetch peers', rebuild report.
cd "$(dirname "$0")"
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
. ./config
python3 claude_usage.py collect || exit 1
gh api -X PATCH "gists/$MY_GIST" --input data/.payload.json >/dev/null || echo "gist upload failed"
rm -f data/peer*.json
i=0
for p in $PEERS; do
  i=$((i+1))
  curl -fsSL "https://gist.githubusercontent.com/$p/raw/usage.json" -o "data/peer$i.json" || echo "peer $p unreachable"
done
python3 claude_usage.py report
