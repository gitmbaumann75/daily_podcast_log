# daily_podcast_log

The "Daily Podcast Picks" routine runs on weekdays, picks 5 podcast episodes, sends them
over Telegram, and logs them here.

## How freshness is enforced

Picks used to be found by web search, which ranks pages by links rather than by date, so old
episodes kept surfacing. Now the publish date comes from each show's own feed, where it is a
fact rather than a judgment call, and episodes past their cutoff are discarded before the
picker ever sees them:

| bucket | cutoff | shows |
| --- | --- | --- |
| `news` | 5 days | daily news, current events, markets |
| `standard` | 30 days | everything else |

## Files

| file | what it does |
| --- | --- |
| `shows.json` | the shows to pull from. Edit this to add or drop one. |
| `fetch_candidates.py` | reads every show's feed, returns only fresh episodes |
| `append_picks.py` | validates the day's picks and appends them to the log |
| `recommended.json` | every episode ever recommended |
| `routine-prompt.md` | a tracked copy of the routine's prompt |

## Running it by hand

```bash
python3 fetch_candidates.py --self-test      # check the feeds are reachable
python3 fetch_candidates.py --resolve        # fill in missing show ids (run once)
python3 fetch_candidates.py --pretty         # list today's fresh candidates
python3 append_picks.py picks.json --dry-run # validate picks without writing
```

Everything uses only the Python standard library — there is nothing to install.

### Adding a show

Add an entry to the `shows` list in `shows.json` with the show's name, a `bucket`
(`"news"` or `"standard"`), and `"favorite": false`. Leave `apple_id` and `feed_url` as
`null`, run `python3 fetch_candidates.py --resolve` to fill them in, check that the name it
matched is the show you meant, and commit the file.

## `recommended.json` format

A flat JSON array, oldest first. Each entry:

| field | meaning |
| --- | --- |
| `title` | episode title |
| `show` | podcast name |
| `url` | direct Spotify or Apple Podcasts episode link |
| `date_recommended` | the day it was sent, `YYYY-MM-DD` |
| `published_date` | the episode's own publish date, `YYYY-MM-DD` |

`published_date` was added in September 2026; entries before that lack it. It exists so
freshness can be audited after the fact — without it there is no way to tell whether a pick
was new or years old.

## Network requirement

`fetch_candidates.py` needs to reach `itunes.apple.com` (and podcast feed hosts, if it falls
back to RSS). If the routine's environment blocks those, `--self-test` will say so, and the
routine falls back to search-based picking with manual date checks.
