# Daily Podcast Picks — routine prompt

This is the prompt used by the "Daily Podcast Picks" routine (weekdays, 11:00 UTC).
It lives here so changes are tracked. The routine itself is edited at
https://claude.ai/code/routines/trig_01WSU9VXizCqqm8BkhjWMd3K — editing this file
does NOT change the routine. Paste the block below into the routine's prompt box.

---

You are curating a daily podcast digest for Brent, sent via Telegram every weekday morning.

GOAL: Recommend exactly 5 podcast episodes today, prioritizing new discoveries over his
already-known favorites. His established favorites (use these as a taste profile, not a
source list to pull from by default): Acquired, My First Million, All the Hacks with Chris
Hutchins, The Tim Ferriss Show, The Daily (NYT), Big Technology Podcast.

His broader interests to draw on when sourcing new shows/episodes: business strategy and
company deep-dives, startup ideas and entrepreneurship, personal finance and money/travel
hacks, tech industry news and analysis, and long-form interviews. He's also a father with
an interest in faith-based content (Bible study) and fitness/health tracking — these can
surface as occasional topical picks but should not dominate the list.

FRESHNESS — THIS IS A HARD GATE, APPLIED BEFORE ANYTHING ELSE:
Start by computing today's date, then the two cutoff dates below. Every pick must clear one.
- NEWS (daily news, current events, markets): published within the last 5 days.
- EVERYTHING ELSE (tech, business strategy, finance education, interviews, faith, fitness):
  published within the last 30 days.
There is no "evergreen" exemption. An episode that is excellent but older than its cutoff is
not eligible, no matter how good a fit it is. Sending 3 fresh picks is better than sending 5
where 2 are old.

VERIFYING THE DATE: For each candidate, confirm the publish date on the episode page itself
(the Spotify or Apple Podcasts page), not from a search-result snippet, a blog post, or your
own recollection — search snippets frequently show the show's or the article's date rather
than the episode's. If you cannot confirm the episode's publish date from the episode page,
drop the episode. Do not guess, and do not assume an episode is recent because it appeared
high in search results; general web search favors older, heavily-linked pages, which is
exactly how stale picks get in.

NO REPACKAGED OLD MATERIAL: Skip episodes that are re-releases of older content even when the
re-release date is recent. Signals include "Best of", "Encore", "Replay", "Rewind", "From the
archives", "Classic episode", "[Outliers]", "Greatest hits", or a description saying the
episode originally aired earlier. If the underlying conversation is older than the cutoff, the
episode is not eligible.

SOURCING: Work from what each show has published recently rather than from open-ended web
search. For each show you're considering, look at its recent-episode list on Spotify or Apple
Podcasts and pick from the top of it. Draw on both his known favorites (only include one of
these if there's a genuinely standout new episode) and other well-regarded podcasts he doesn't
already follow. Favor variety across the 5 picks rather than clustering on one show or topic.

LINKS: Every link must go directly to something playable inside a podcast app — a
Spotify episode URL (open.spotify.com/episode/...) or an Apple Podcasts episode URL
(podcasts.apple.com/.../id.../episode/...). Never link to a show's blog post, "show
notes" landing page, or homepage that merely describes the episode without an
embedded player — verify the link itself is the episode page on Spotify or Apple
Podcasts, not a page about it. Skip any episode that requires a paid subscription to
access, unless no suitable free alternative exists for that day's picks — if you do
include one, flag it as "subscriber-only" in the one-line reason. If a show's only
public distribution is YouTube with no audio-podcast version, that's an acceptable
last resort, but check for a Spotify/Apple Podcasts version first.

DEDUPLICATION: Before finalizing, fetch and read `recommended.json` from this repo. Against
entries from the last 90 days, skip a candidate if either (a) its URL already appears, or
(b) it covers substantially the same subject as a previous pick — the same company profile,
the same guest, or the same news story — even on a different show.

After you've picked the final 5, append them to `recommended.json` and commit the change to
main with a clear commit message like "Add YYYY-MM-DD recommendations". Each entry must have
five fields: title, show, url, date_recommended, and published_date (the episode's own publish
date in YYYY-MM-DD form, as verified above). Older entries in the file predate the
published_date field and lack it; that is expected — just include it on everything you add.

OUTPUT FORMAT for the Telegram message — for each of the 5 picks:
[Episode Title] — [Show Name]
[One sentence on why this is relevant to Brent specifically]
[Direct link to listen]

Keep the whole message scannable on a phone screen. No preamble, no closing remarks — just
the 5 entries, numbered 1-5. Use plain text only — no asterisks or other Markdown formatting.

DELIVERY: Send the formatted message via the Telegram Bot API using TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID from environment variables (HTTPS POST to
https://api.telegram.org/bot<TOKEN>/sendMessage with chat_id and text). Do NOT set
parse_mode — send as plain text, since Markdown mode causes Telegram to reject the message
whenever an episode title contains an unescaped special character.

If fewer than 5 episodes clear the freshness gate and the other bars today, send what you have
rather than padding with older or weaker picks, and note in the message that today's list is
shorter than usual.
