#!/usr/bin/env python3
"""Per-machine and per-project Claude Code token usage.

  python3 claude_usage.py collect   # read ~/.claude/projects logs -> data/usage.json
  python3 claude_usage.py report    # table from data/usage.json + data/peer*.json
"""
import glob, json, os, socket, sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
WINDOWS = {"5h": timedelta(hours=5), "1d": timedelta(days=1), "7d": timedelta(days=7)}


def zero():
    return {f: 0 for f in FIELDS}


def add(dst, u):
    for f in FIELDS:
        dst[f] += u.get(f) or 0


def work(t):
    # everything except cache reads, which are cheap and dominate raw counts
    return t["input_tokens"] + t["output_tokens"] + t["cache_creation_input_tokens"]


def fmt(n):
    return f"{n/1e6:.2f}M" if n >= 1e6 else f"{n/1e3:.1f}K" if n >= 1e3 else str(n)


def collect():
    now = datetime.now(timezone.utc)
    oldest = now - max(WINDOWS.values())
    win = {k: {"totals": zero(), "by_model": {}, "by_project": {}} for k in WINDOWS}
    seen = set()
    for path in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True):
        if datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < oldest:
            continue
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
                if ts < oldest:
                    continue
                key = (msg.get("id"), d.get("requestId"))  # streamed messages repeat
                if key in seen:
                    continue
                seen.add(key)
                model = msg.get("model", "?")
                project = os.path.basename((d.get("cwd") or os.path.dirname(path)).rstrip("/")) or "?"
                for k, span in WINDOWS.items():
                    if ts >= now - span:
                        w = win[k]
                        add(w["totals"], u)
                        add(w["by_model"].setdefault(model, zero()), u)
                        add(w["by_project"].setdefault(project, zero()), u)

    doc = {"machine": socket.gethostname().split(".")[0],
           "updated": datetime.now().isoformat(timespec="minutes"), "windows": win}
    os.makedirs(DATA, exist_ok=True)
    body = json.dumps(doc, indent=1)
    with open(os.path.join(DATA, "usage.json"), "w") as fh:
        fh.write(body)
    with open(os.path.join(DATA, ".payload.json"), "w") as fh:  # for PATCH /gists/{id}
        json.dump({"files": {"usage.json": {"content": body}}}, fh)


def report():
    docs = {}
    for p in [os.path.join(DATA, "usage.json")] + sorted(glob.glob(os.path.join(DATA, "peer*.json"))):
        try:
            with open(p) as fh:
                d = json.load(fh)
            docs.setdefault(d["machine"], d)
        except (OSError, ValueError, KeyError):
            continue

    out = [f"Generated {datetime.now():%Y-%m-%d %H:%M}.  share = input + output + cache writes (cache reads excluded)"]
    for k in WINDOWS:
        rows = [(m, d["windows"][k]) for m, d in docs.items() if k in d.get("windows", {})]
        total = sum(work(w["totals"]) for _, w in rows) or 1
        out += ["", f"=== last {k} ===", "",
                f"{'machine':<20}{'output':>9}{'in+cw':>10}{'cache rd':>10}{'share':>8}  updated"]
        for m, w in sorted(rows, key=lambda r: -work(r[1]["totals"])):
            t = w["totals"]
            out.append(f"{m:<20}{fmt(t['output_tokens']):>9}"
                       f"{fmt(t['input_tokens'] + t['cache_creation_input_tokens']):>10}"
                       f"{fmt(t['cache_read_input_tokens']):>10}{100*work(t)/total:>7.1f}%  {docs[m]['updated']}")
        projects = [(p, m, t) for m, w in rows for p, t in w["by_project"].items() if work(t)]
        if projects:
            out += ["", f"{'project':<32}{'machine':<20}{'output':>9}{'share':>8}"]
            for p, m, t in sorted(projects, key=lambda r: -work(r[2]))[:15]:
                out.append(f"{p[:31]:<32}{m:<20}{fmt(t['output_tokens']):>9}{100*work(t)/total:>7.1f}%")
    text = "\n".join(out) + "\n"
    with open(os.path.join(DATA, "report.txt"), "w") as fh:
        fh.write(text)
    print(text)

    template = os.path.join(HERE, "dashboard_template.html")
    if os.path.exists(template):
        with open(template) as fh:
            html = fh.read()
        data = json.dumps({"generated": datetime.now().isoformat(timespec="minutes"), "machines": docs})
        with open(os.path.join(DATA, "dashboard.html"), "w") as fh:
            fh.write(html.replace("__DATA__", data.replace("</", "<\\/")))


if __name__ == "__main__":
    {"collect": collect, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
