#!/usr/bin/env python3
"""Validate today's picks and append them to recommended.json.

This is the last gate. It refuses to write anything stale, undated, duplicated,
or pointing somewhere that isn't playable, so a bad pick cannot reach the log
even if the earlier steps let it slip through.

Usage:
    python3 append_picks.py picks.json
    cat picks.json | python3 append_picks.py -
    python3 append_picks.py picks.json --dry-run

picks.json is a JSON array of objects:
    [{"title": "...", "show": "...", "url": "https://open.spotify.com/episode/...",
      "published_date": "2026-09-20", "bucket": "standard"}]

bucket is optional and defaults to "standard"; date_recommended defaults to today.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "recommended.json")

CUTOFFS = {"news": 5, "standard": 30}

PLAYABLE = (
    re.compile(r"^https://open\.spotify\.com/episode/[A-Za-z0-9]+"),
    re.compile(r"^https://podcasts\.apple\.com/.+[?&]i=\d+"),
    re.compile(r"^https://podcasts\.apple\.com/.+/episode/"),
)

REQUIRED = ("title", "show", "url", "published_date")


def check(picks, existing, today, allow_old):
    """Return (clean_picks, errors)."""
    errors = []
    seen_urls = {e.get("url", "").strip() for e in existing if e.get("url")}
    clean, batch_urls = [], set()

    for i, pick in enumerate(picks, 1):
        where = "pick %d (%s)" % (i, str(pick.get("title", "untitled"))[:50])

        if not isinstance(pick, dict):
            errors.append("%s: not a JSON object" % where)
            continue

        missing = [f for f in REQUIRED if not str(pick.get(f, "")).strip()]
        if missing:
            errors.append("%s: missing %s" % (where, ", ".join(missing)))
            continue

        url = pick["url"].strip()
        if not any(p.match(url) for p in PLAYABLE):
            errors.append("%s: url is not a Spotify or Apple Podcasts episode link "
                          "(%s)" % (where, url[:80]))
        if url in seen_urls:
            errors.append("%s: already in recommended.json" % where)
        if url in batch_urls:
            errors.append("%s: duplicated within today's picks" % where)
        batch_urls.add(url)

        bucket = pick.get("bucket", "standard")
        if bucket not in CUTOFFS:
            errors.append("%s: unknown bucket %r (use news or standard)" % (where, bucket))
            bucket = "standard"

        try:
            published = dt.date.fromisoformat(pick["published_date"].strip())
        except (ValueError, AttributeError):
            errors.append("%s: published_date %r is not YYYY-MM-DD"
                          % (where, pick.get("published_date")))
            continue

        age = (today - published).days
        if age < 0:
            errors.append("%s: published_date %s is in the future"
                          % (where, published.isoformat()))
        elif age > CUTOFFS[bucket] and not allow_old:
            errors.append("%s: %d days old, over the %d-day limit for %s"
                          % (where, age, CUTOFFS[bucket], bucket))

        clean.append({
            "title": pick["title"].strip(),
            "show": pick["show"].strip(),
            "url": url,
            "date_recommended": str(pick.get("date_recommended") or today.isoformat()),
            "published_date": published.isoformat(),
        })

    return clean, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("picks", help="path to the picks JSON file, or - for stdin")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate only; do not write recommended.json")
    ap.add_argument("--allow-old", action="store_true",
                    help="escape hatch: skip the age check (do not use in the routine)")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.picks == "-" else open(args.picks, encoding="utf-8").read()
    try:
        picks = json.loads(raw)
    except json.JSONDecodeError as exc:
        print("Could not parse the picks as JSON: %s" % exc, file=sys.stderr)
        return 2
    if not isinstance(picks, list):
        print("Expected a JSON array of picks.", file=sys.stderr)
        return 2

    with open(LOG_PATH, encoding="utf-8") as fh:
        existing = json.load(fh)

    clean, errors = check(picks, existing, dt.date.today(), args.allow_old)

    if errors:
        print("Rejected %d problem(s); nothing was written:" % len(errors), file=sys.stderr)
        for err in errors:
            print("  - %s" % err, file=sys.stderr)
        return 1

    if args.dry_run:
        print("OK: %d pick(s) valid. Nothing written (--dry-run)." % len(clean),
              file=sys.stderr)
        return 0

    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        json.dump(existing + clean, fh, indent=2)
        fh.write("\n")

    print("Appended %d pick(s) to recommended.json." % len(clean), file=sys.stderr)
    for pick in clean:
        print("  %s - %s (published %s)"
              % (pick["show"], pick["title"][:60], pick["published_date"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
