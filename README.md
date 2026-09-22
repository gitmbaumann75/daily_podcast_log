# daily_podcast_log

Log of podcast episodes recommended by the "Daily Podcast Picks" routine, which runs
weekdays and sends 5 picks over Telegram.

## Files

- `recommended.json` — every episode ever recommended, appended to on each run.
- `routine-prompt.md` — a copy of the routine's prompt, kept here so changes are
  tracked in git. The live routine is edited on claude.ai; this file is a record, not
  the source of truth.

## `recommended.json` format

A flat JSON array, oldest first. Each entry:

| field | meaning |
| --- | --- |
| `title` | episode title |
| `show` | podcast name |
| `url` | direct Spotify or Apple Podcasts episode link |
| `date_recommended` | the day it was sent, `YYYY-MM-DD` |
| `published_date` | the episode's own publish date, `YYYY-MM-DD` |

`published_date` was added in September 2026. Entries before that lack the field.
It exists so freshness can be audited after the fact — without it there is no way to
tell whether a pick was new or years old.
