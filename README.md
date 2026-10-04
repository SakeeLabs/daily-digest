# daily-digest

A personal, read-only daily digest. Once a day it reads a short list of public sources and produces a private summary for one person. It is non-commercial and has no users other than its owner.

## What it reads

| Source | How | Volume |
|---|---|---|
| **Reddit** — ~17 public subreddits listed in [`config/subreddits.json`](config/subreddits.json) | Official Reddit Data API, application-only OAuth, read-only listing endpoints (`/top?t=day`, `/new`, `/api/info`) | About 20–40 requests per day |
| **GitHub** — a handful of curated "awesome" lists of agent skills and MCP servers | `git clone` + diff, to see which repositories were newly added | ~9 shallow clones per day |

## What it does with the data

It writes a short daily summary for the owner's private dashboard. Every item links back to its original Reddit thread or GitHub repository; nothing is republished.

## What it never does

- Post, comment, vote, send messages, or moderate on Reddit
- Interact with any user, or read private data or user profiles
- Sell, share, or republish Reddit content
- Use Reddit data to train AI models

See [DATA_POLICY.md](DATA_POLICY.md) for retention and deletion rules.

## Reddit details

- **Account:** u/SakeeDigestBot (dedicated, read-only)
- **User-Agent:** `script:sakee-daily-digest:v1.0 (by /u/SakeeDigestBot)`
- **Auth:** application-only OAuth (client credentials). No account password is used or stored.
- **Rate:** at most one request every 1.2 seconds, with back-off on `429` and server errors
- **Why not Devvit:** this is an off-platform, scheduled reader for one person, not an app installed in a subreddit, so it doesn't fit Devvit's model.

## Layout

```
config/subreddits.json     subreddits and limits
reddit/reddit_digest.py    Reddit reader (read-only)
github/collect.py          finds repos newly added to curated GitHub lists
```

## Running

```bash
export REDDIT_CLIENT_ID=...       # from a "script" app at reddit.com/prefs/apps
export REDDIT_CLIENT_SECRET=...   # never commit this
python3 reddit/reddit_digest.py   # writes to ./out (git-ignored)

python3 github/collect.py 30 > out/github.json
```

Credentials are read from environment variables (or CI secrets) only. Output goes to `out/`, which is git-ignored, so Reddit content is never committed to this public repository.

## Contact

Open an issue on this repository.
