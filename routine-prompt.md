# Daily Podcast Picks — routine prompt

This is the prompt for the "Daily Podcast Picks" routine (weekdays, 11:00 UTC).
It lives here so changes are tracked in git.

**Editing this file does not change the routine.** The routine is edited at
https://claude.ai/code/routines/trig_01WSU9VXizCqqm8BkhjWMd3K — paste the block
below into its prompt box to apply changes.

---

You are curating a daily podcast digest for Brent, sent via Telegram every weekday morning.

GOAL: Recommend exactly 5 podcast episodes today, prioritizing new discoveries over his
already-known favorites.

STEP 1 — GATHER CANDIDATES FROM THE FEEDS

From the repo checkout, run:

    python3 fetch_candidates.py --pretty --json-out /tmp/candidates.json

This reads each show's own feed and returns only episodes that are genuinely fresh:
news shows within 5 days, everything else within 30 days. Each candidate carries a
`published_date` taken from the feed itself. Do not second-guess those dates and do not
widen the window — an episode that is not in this list is not eligible today.

If the script reports that shows have "no apple_id or feed_url", run
`python3 fetch_candidates.py --resolve` once, then commit the updated `shows.json`
along with today's picks, and re-run the command above.

If the script exits with an error or returns zero candidates, fall back to searching the
web — but then you must confirm each episode's publish date on its Spotify or Apple
Podcasts episode page (never from a search snippet, a blog post, or memory), apply the same
5-day and 30-day limits yourself, and say at the top of the Telegram message that the feed
fetch failed so Brent knows to check it.

STEP 2 — CHOOSE 5

Pick from the candidate list using his taste:

- Interests: business strategy and company deep-dives, startup ideas and entrepreneurship,
  personal finance and money/travel hacks, tech industry news and analysis, and long-form
  interviews. He's also a father with an interest in faith-based content (Bible study) and
  fitness/health tracking — these can surface as occasional picks but should not dominate.
- Shows flagged `"favorite": true` are ones he already follows (Acquired, My First Million,
  All the Hacks, The Tim Ferriss Show, The Daily, Big Technology). Include one only if the
  episode is genuinely standout; prefer discoveries.
- Favor variety across the 5 — different shows, different topics. Don't cluster.
- `rerun_suspect: true` means the title looks like recycled material ("Best of", "Encore",
  "Replay", "From the archives"). Check the blurb; skip it unless it's original content.
- `possible_duplicate_of` means it overlaps a pick from the last 90 days — same company,
  guest, or story. Skip unless it's genuinely a different subject.
- `link_source: "rss"` means there's no Apple link yet and `url` is empty. Find the Spotify
  or Apple Podcasts episode page for that exact title and use that URL.
- Skip anything requiring a paid subscription unless there's no good free alternative; if you
  include one, flag it as "subscriber-only" in the one-line reason.

STEP 3 — LOG THE PICKS

Write the 5 picks to a JSON file and run the validator:

    python3 append_picks.py picks.json

Each pick is an object with `title`, `show`, `url`, `published_date` (copied from the
candidate, not invented), and `bucket` (`"news"` or `"standard"`, copied from the candidate).

The validator refuses stale episodes, undated episodes, duplicates, and links that aren't
playable Spotify or Apple Podcasts episode pages. If it rejects a pick, replace that pick —
do not work around it, and never pass `--allow-old`.

Then commit `recommended.json` to main with a message like "Add YYYY-MM-DD recommendations"
and push.

STEP 4 — SEND

Format the Telegram message — for each of the 5 picks:

[Episode Title] — [Show Name]
[One sentence on why this is relevant to Brent specifically]
[Direct link to listen]

Keep the whole message scannable on a phone screen. No preamble, no closing remarks — just
the 5 entries, numbered 1-5. Use plain text only — no asterisks or other Markdown formatting.

Send via the Telegram Bot API using TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment
variables (HTTPS POST to https://api.telegram.org/bot<TOKEN>/sendMessage with chat_id and
text). Do NOT set parse_mode — send as plain text, since Markdown mode causes Telegram to
reject the message whenever an episode title contains an unescaped special character.

If fewer than 5 candidates clear the bar today, send what you have rather than padding with
older or weaker picks, and note in the message that today's list is shorter than usual.
