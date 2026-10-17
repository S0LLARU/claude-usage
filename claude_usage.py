#!/usr/bin/env python3
"""Per-machine Claude Code token usage.

Each machine reads its own ~/.claude/projects/**/*.jsonl, writes a summary
to a shared folder (iCloud Drive by default), then prints a table comparing
all machines found there.

  python3 claude_usage.py            # last 7 days
  python3 claude_usage.py --days 1   # last 24 hours
  python3 claude_usage.py --hours 5  # current ~5h window
"""
import argparse, glob, json, os, socket
from datetime import datetime, timedelta, timezone

SHARED = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/claude-usage")
FIELDS = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]


def collect(since):
    totals = {f: 0 for f in FIELDS}
    by_model, seen = {}, set()
    for path in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True):
        with open(path, errors="ignore") as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    d = json.loads(line)
                    msg = d["message"]
                    u = msg["usage"]
                    ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                except (ValueError, KeyError, TypeError):
                    continue
                if ts < since:
                    continue
                key = (msg.get("id"), d.get("requestId"))  # streamed messages repeat
                if key in seen:
                    continue
                seen.add(key)
                m = by_model.setdefault(msg.get("model", "?"), {f: 0 for f in FIELDS})
                for f in FIELDS:
                    v = u.get(f) or 0
                    totals[f] += v
                    m[f] += v
    return totals, by_model


def fmt(n):
    return f"{n/1e6:.2f}M" if n >= 1e6 else f"{n/1e3:.1f}K" if n >= 1e3 else str(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--hours", type=float)
    ap.add_argument("--shared", default=SHARED)
    ap.add_argument("--name", default=socket.gethostname().split(".")[0])
    a = ap.parse_args()

    span = timedelta(hours=a.hours) if a.hours else timedelta(days=a.days)
    since = datetime.now(timezone.utc) - span
    label = f"{a.hours}h" if a.hours else f"{a.days:g}d"

    totals, by_model = collect(since)
    os.makedirs(a.shared, exist_ok=True)
    with open(os.path.join(a.shared, f"{a.name}_{label}.json"), "w") as fh:
        json.dump({"machine": a.name, "window": label, "updated": datetime.now().isoformat(timespec="minutes"),
                   "totals": totals, "by_model": by_model}, fh, indent=1)

    rows = []
    for p in sorted(glob.glob(os.path.join(a.shared, f"*_{label}.json"))):
        with open(p) as fh:
            rows.append(json.load(fh))

    # "work" = everything except cache reads, which are cheap and dominate raw counts
    def work(t):
        return t["input_tokens"] + t["output_tokens"] + t["cache_creation_input_tokens"]

    all_work = sum(work(r["totals"]) for r in rows) or 1
    all_out = sum(r["totals"]["output_tokens"] for r in rows) or 1
    out = [f"Window: last {label}   (generated {datetime.now():%Y-%m-%d %H:%M} on {a.name})", "",
           f"{'machine':<18}{'output':>10}{'input+cw':>11}{'cache rd':>11}{'share':>8}{'out %':>8}  updated"]
    for r in rows:
        t = r["totals"]
        out.append(f"{r['machine']:<18}{fmt(t['output_tokens']):>10}"
                   f"{fmt(t['input_tokens'] + t['cache_creation_input_tokens']):>11}"
                   f"{fmt(t['cache_read_input_tokens']):>11}"
                   f"{100*work(t)/all_work:>7.1f}%{100*t['output_tokens']/all_out:>7.1f}%  {r['updated']}")
    report = "\n".join(out) + "\n"
    with open(os.path.join(a.shared, f"report_{label}.txt"), "w") as fh:
        fh.write(report)
    print("\n" + report)
    print(f"This machine by model ({a.name}):")
    for model, t in sorted(by_model.items(), key=lambda kv: -work(kv[1])):
        print(f"  {model:<28} out {fmt(t['output_tokens']):>8}   in+cw {fmt(t['input_tokens'] + t['cache_creation_input_tokens']):>8}")

if __name__ == "__main__":
    main()
