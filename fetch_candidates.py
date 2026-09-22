#!/usr/bin/env python3
"""Collect fresh podcast episodes for the daily digest.

Every episode comes back with a publish date read straight from the show's own
feed, so freshness is a fact rather than a judgment call. Episodes past their
bucket's cutoff are dropped here and never reach the picker.

Usage:
    python3 fetch_candidates.py                 # print candidates as JSON
    python3 fetch_candidates.py --pretty        # print a readable summary too
    python3 fetch_candidates.py --resolve       # fill in missing ids in shows.json
    python3 fetch_candidates.py --self-test     # just check network access

Exit codes:
    0  candidates found
    3  no candidates (every show unreachable, or nothing fresh enough)
"""

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SHOWS_PATH = os.path.join(HERE, "shows.json")
LOG_PATH = os.path.join(HERE, "recommended.json")

# Freshness cutoffs in days, by bucket. Nothing older than these gets through.
CUTOFFS = {"news": 5, "standard": 30}

ITUNES_SEARCH = "https://itunes.apple.com/search"
ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
USER_AGENT = "daily-podcast-log/1.0 (+https://github.com/gitmbaumann75/daily_podcast_log)"
TIMEOUT = 20

# Titles that signal recycled material. These only flag an episode for the
# picker to look at; they do not drop it, because some shows legitimately use
# words like "classic" in original episodes.
RERUN_PATTERNS = re.compile(
    r"\b(best of|encore|replay|rewind|re-?run|re-?release|throwback|"
    r"from the archives?|classic episode|greatest hits|revisited)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "it", "its", "at", "by", "from", "how", "why", "what", "we", "you", "your",
    "this", "that", "not", "but", "as", "be", "are", "was", "were", "our", "my",
    "ep", "episode", "part", "pod", "podcast", "show", "vs", "into", "about",
}


def log(msg):
    print(msg, file=sys.stderr)


def get(url, params=None):
    """GET a URL and return raw bytes. Honors HTTPS_PROXY from the environment."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def get_json(url, params=None):
    return json.loads(get(url, params).decode("utf-8", "replace"))


def norm(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())


def tokens(title):
    return {w for w in norm(title).split() if len(w) > 2 and w not in STOPWORDS}


# --------------------------------------------------------------------------
# Resolving shows to Apple ids
# --------------------------------------------------------------------------

def resolve_show(show):
    """Look up a show by name and return (apple_id, feed_url, matched_name)."""
    data = get_json(ITUNES_SEARCH, {
        "term": show["name"], "media": "podcast", "entity": "podcast", "limit": 5,
    })
    results = data.get("results") or []
    if not results:
        return None, None, None
    wanted = tokens(show["name"])
    best, best_score = None, -1.0
    for r in results:
        got = tokens(r.get("collectionName", ""))
        overlap = len(wanted & got) / max(len(wanted | got), 1)
        if overlap > best_score:
            best, best_score = r, overlap
    if best_score < 0.34:
        log("  ! %r best match was %r - too different, skipping"
            % (show["name"], best.get("collectionName")))
        return None, None, None
    return best.get("collectionId"), best.get("feedUrl"), best.get("collectionName")


# --------------------------------------------------------------------------
# Fetching episodes
# --------------------------------------------------------------------------

def episodes_from_itunes(apple_id, limit):
    """Apple's lookup API: gives an exact release date AND a playable Apple link."""
    data = get_json(ITUNES_LOOKUP, {
        "id": apple_id, "media": "podcast", "entity": "podcastEpisode", "limit": limit,
    })
    out = []
    for r in data.get("results", []):
        if r.get("wrapperType") != "podcastEpisode":
            continue
        raw = r.get("releaseDate")
        if not raw:
            continue
        try:
            when = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        url = r.get("trackViewUrl")
        if not url:
            continue
        out.append({
            "title": (r.get("trackName") or "").strip(),
            "url": url,
            "published": when,
            "blurb": (r.get("shortDescription") or r.get("description") or "").strip(),
            "source": "apple",
        })
    return out


def episodes_from_rss(feed_url, limit):
    """Fallback when the Apple API is unavailable. Dates come from <pubDate>.

    RSS has no Apple/Spotify episode link, so url is left empty and the picker
    has to find a playable link for the title. The date is still authoritative,
    which is the part that matters.
    """
    root = ET.fromstring(get(feed_url))
    channel = root.find("channel")
    items = (channel.findall("item") if channel is not None else root.findall(".//item"))
    out = []
    for item in items[:limit]:
        raw = item.findtext("pubDate")
        if not raw:
            continue
        try:
            when = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        out.append({
            "title": (item.findtext("title") or "").strip(),
            "url": "",
            "published": when,
            "blurb": (item.findtext("description") or "").strip()[:400],
            "source": "rss",
        })
    return out


def collect_show(show, limit):
    """Return (candidates, error_message). Tries Apple first, then RSS."""
    errors = []
    if show.get("apple_id"):
        try:
            eps = episodes_from_itunes(show["apple_id"], limit)
            if eps:
                return eps, None
            errors.append("Apple returned no episodes")
        except Exception as exc:
            errors.append("Apple lookup failed (%s)" % exc)
    if show.get("feed_url"):
        try:
            eps = episodes_from_rss(show["feed_url"], limit)
            if eps:
                return eps, None
            errors.append("RSS feed had no dated items")
        except Exception as exc:
            errors.append("RSS fetch failed (%s)" % exc)
    if not show.get("apple_id") and not show.get("feed_url"):
        errors.append("no apple_id or feed_url - run --resolve")
    return [], "; ".join(errors)


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------

def load_recent_log(days):
    """Previously recommended episodes from the last N days."""
    if not os.path.exists(LOG_PATH):
        return [], set()
    with open(LOG_PATH, encoding="utf-8") as fh:
        entries = json.load(fh)
    cutoff = dt.date.today() - dt.timedelta(days=days)
    recent = []
    for e in entries:
        try:
            when = dt.date.fromisoformat(e.get("date_recommended", ""))
        except ValueError:
            continue
        if when >= cutoff:
            recent.append(e)
    all_urls = {e.get("url", "").strip() for e in entries if e.get("url")}
    return recent, all_urls


def duplicate_note(candidate, recent):
    """Flag a candidate that covers the same ground as a recent pick."""
    cand = tokens(candidate["title"])
    if not cand:
        return None
    for prev in recent:
        prev_tokens = tokens(prev.get("title", ""))
        if not prev_tokens:
            continue
        shared = cand & prev_tokens
        overlap = len(shared) / max(len(cand | prev_tokens), 1)
        if overlap >= 0.4 or len(shared) >= 3:
            return "overlaps %r (%s, %s)" % (
                prev.get("title", "")[:60], prev.get("show", ""),
                prev.get("date_recommended", ""))
    return None


def build_candidates(shows, per_show, dedup_days, workers):
    today = dt.datetime.now(dt.timezone.utc)
    recent, seen_urls = load_recent_log(dedup_days)
    candidates, failures = [], []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(collect_show, s, per_show): s for s in shows}
        for future in concurrent.futures.as_completed(futures):
            show = futures[future]
            try:
                episodes, error = future.result()
            except Exception as exc:  # defensive: a worker should not kill the run
                episodes, error = [], "unexpected error (%s)" % exc
            if error:
                failures.append((show["name"], error))
            cutoff_days = CUTOFFS.get(show.get("bucket", "standard"), 30)
            for ep in episodes:
                age = (today - ep["published"]).days
                if age < 0:
                    age = 0
                if age > cutoff_days:
                    continue  # the hard freshness gate
                if ep["url"] and ep["url"].strip() in seen_urls:
                    continue  # already recommended, at any point
                candidates.append({
                    "show": show["name"],
                    "title": ep["title"],
                    "url": ep["url"],
                    "published_date": ep["published"].date().isoformat(),
                    "days_old": age,
                    "bucket": show.get("bucket", "standard"),
                    "favorite": bool(show.get("favorite")),
                    "rerun_suspect": bool(RERUN_PATTERNS.search(ep["title"])),
                    "possible_duplicate_of": duplicate_note(ep, recent),
                    "blurb": ep["blurb"][:300],
                    "link_source": ep["source"],
                })

    candidates.sort(key=lambda c: (c["days_old"], c["show"]))
    return candidates, failures


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_resolve(config):
    changed = 0
    for show in config["shows"]:
        if show.get("apple_id") and show.get("feed_url"):
            continue
        log("resolving %s ..." % show["name"])
        try:
            apple_id, feed_url, matched = resolve_show(show)
        except Exception as exc:
            log("  ! lookup failed: %s" % exc)
            continue
        if not apple_id:
            continue
        show["apple_id"] = apple_id
        show["feed_url"] = feed_url
        changed += 1
        note = "" if matched == show["name"] else "  (matched %r)" % matched
        log("  -> id %s%s" % (apple_id, note))
    if changed:
        with open(SHOWS_PATH, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        log("\nUpdated shows.json for %d show(s). Review the matches, then commit it."
            % changed)
    else:
        log("\nNothing resolved.")
    return 0 if changed else 3


def cmd_self_test():
    log("Checking access to itunes.apple.com ...")
    try:
        data = get_json(ITUNES_SEARCH, {
            "term": "acquired", "media": "podcast", "entity": "podcast", "limit": 1})
    except Exception as exc:
        log("FAILED: %s" % exc)
        log("\nThe environment this runs in cannot reach the Apple podcast API.")
        log("The routine needs a network policy that allows itunes.apple.com.")
        return 3
    name = (data.get("results") or [{}])[0].get("collectionName", "?")
    log("OK - reached Apple and found %r." % name)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resolve", action="store_true",
                    help="fill in missing apple_id/feed_url in shows.json and exit")
    ap.add_argument("--self-test", action="store_true",
                    help="check that the podcast API is reachable and exit")
    ap.add_argument("--per-show", type=int, default=8,
                    help="how many recent episodes to examine per show (default 8)")
    ap.add_argument("--dedup-days", type=int, default=90,
                    help="window for subject-overlap warnings (default 90)")
    ap.add_argument("--workers", type=int, default=8, help="parallel fetches")
    ap.add_argument("--pretty", action="store_true",
                    help="also print a readable summary to stderr")
    ap.add_argument("--json-out", help="write the candidate JSON to this file")
    args = ap.parse_args()

    if args.self_test:
        return cmd_self_test()

    with open(SHOWS_PATH, encoding="utf-8") as fh:
        config = json.load(fh)

    if args.resolve:
        return cmd_resolve(config)

    candidates, failures = build_candidates(
        config["shows"], args.per_show, args.dedup_days, args.workers)

    if failures:
        log("Could not read %d of %d shows:" % (len(failures), len(config["shows"])))
        for name, error in sorted(failures):
            log("  - %s: %s" % (name, error))
        log("")

    payload = json.dumps(candidates, indent=2, ensure_ascii=False)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        log("Wrote %d candidates to %s" % (len(candidates), args.json_out))
    else:
        print(payload)

    if args.pretty:
        log("\n%d fresh candidates (news <=%dd, everything else <=%dd):"
            % (len(candidates), CUTOFFS["news"], CUTOFFS["standard"]))
        for c in candidates:
            flags = []
            if c["favorite"]:
                flags.append("favorite")
            if c["rerun_suspect"]:
                flags.append("possible rerun")
            if c["possible_duplicate_of"]:
                flags.append("dupe? " + c["possible_duplicate_of"])
            if not c["url"]:
                flags.append("no apple link - find one")
            suffix = ("  [%s]" % "; ".join(flags)) if flags else ""
            log("  %2dd  %-34s %s%s"
                % (c["days_old"], c["show"][:34], c["title"][:58], suffix))

    return 0 if candidates else 3


if __name__ == "__main__":
    sys.exit(main())
