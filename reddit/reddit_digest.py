#!/usr/bin/env python3
"""Sakee Daily Digest — Reddit reader (read-only).

What it does
  * Gets an application-only OAuth token (client credentials). No user password is used or stored.
  * Reads public listings (/top?t=day and /new) for the subreddits in config/subreddits.json.
  * Keeps only post metadata: id, subreddit, title, score, comment count, permalink, created time,
    flair, and a short excerpt (max 280 chars) of self-text.
  * Purges stored posts that were deleted or removed, and anything older than the retention window.

What it never does
  * Post, comment, vote, message, moderate, or call any endpoint that writes.
  * Read private data, user profiles, or anything outside public subreddit listings.

Credentials come from environment variables only:
  REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME (used only in the User-Agent).
Output is written to OUTPUT_DIR (default ./out), which is git-ignored: Reddit content is never
committed to this public repository.
"""
import base64, json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, 'config', 'subreddits.json')))
OUT = os.environ.get('OUTPUT_DIR', os.path.join(ROOT, 'out'))
RETENTION_DAYS = 30
VERSION = '1.0'
USERNAME = os.environ.get('REDDIT_USERNAME', 'SakeeDigestBot')
USER_AGENT = f'script:sakee-daily-digest:v{VERSION} (by /u/{USERNAME})'
MIN_INTERVAL = 1.2  # seconds between requests — far below the 100 requests/minute free-tier limit


def http(url, data=None, headers=None, retries=3):
    h = {'User-Agent': USER_AGENT, **(headers or {})}
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:  # rate limited or server error: back off
                wait = int(e.headers.get('Retry-After', 0) or 0) or 10 * (attempt + 1)
                time.sleep(min(wait, 120))
                continue
            raise
    raise RuntimeError(f'giving up on {url}')


def token():
    cid, secret = os.environ['REDDIT_CLIENT_ID'], os.environ['REDDIT_CLIENT_SECRET']
    auth = base64.b64encode(f'{cid}:{secret}'.encode()).decode()
    res = http('https://www.reddit.com/api/v1/access_token',
               data=urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode(),
               headers={'Authorization': f'Basic {auth}'})
    return res['access_token']


def slim(p):
    d = p['data']
    text = (d.get('selftext') or '').strip().replace('\n', ' ')
    return {
        'id': d['name'], 'subreddit': d['subreddit'], 'title': d['title'], 'score': d['score'],
        'comments': d['num_comments'], 'url': 'https://www.reddit.com' + d['permalink'],
        'created_utc': d['created_utc'], 'flair': d.get('link_flair_text'),
        'excerpt': text[:280],
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    tok = token()
    auth = {'Authorization': f'bearer {tok}'}
    api = 'https://oauth.reddit.com'
    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    posts, last = {}, 0.0

    def get(path):
        nonlocal last
        delay = MIN_INTERVAL - (time.time() - last)
        if delay > 0:
            time.sleep(delay)
        last = time.time()
        return http(api + path, headers=auth)

    lim = CONFIG.get('per_subreddit_limit', 25)
    for sub in CONFIG['subreddits']:
        for listing in CONFIG.get('listings', ['top_day']):
            path = f'/r/{sub}/top?t=day&limit={lim}' if listing == 'top_day' else f'/r/{sub}/new?limit={lim}'
            try:
                for child in get(path)['data']['children']:
                    if child['kind'] == 't3' and not child['data'].get('over_18'):
                        posts[child['data']['name']] = slim(child)
            except Exception as e:  # one subreddit failing shouldn't stop the run
                print(f'warn: r/{sub} {listing}: {e}', file=sys.stderr)

    json.dump({'date': today, 'user_agent': USER_AGENT, 'posts': list(posts.values())},
              open(os.path.join(OUT, f'reddit-{today}.json'), 'w'), indent=1)

    # Retention + deletion handling for previously stored days.
    cutoff = datetime.date.today() - datetime.timedelta(days=RETENTION_DAYS)
    for name in sorted(os.listdir(OUT)):
        if not (name.startswith('reddit-') and name.endswith('.json')):
            continue
        day = datetime.date.fromisoformat(name[7:17])
        path = os.path.join(OUT, name)
        if day < cutoff:
            os.remove(path)
            continue
        if name == f'reddit-{today}.json':
            continue
        stored = json.load(open(path))
        ids = [p['id'] for p in stored['posts']]
        keep = set()
        for i in range(0, len(ids), 100):  # /api/info accepts up to 100 ids per call
            info = get('/api/info?id=' + ','.join(ids[i:i + 100]))
            for c in info['data']['children']:
                d = c['data']
                if d.get('removed_by_category') or d.get('author') == '[deleted]' or d.get('selftext') in ('[removed]', '[deleted]'):
                    continue
                keep.add(d['name'])
        stored['posts'] = [p for p in stored['posts'] if p['id'] in keep]
        json.dump(stored, open(path, 'w'), indent=1)

    print(f'{len(posts)} posts from {len(CONFIG["subreddits"])} subreddits -> {OUT}')


if __name__ == '__main__':
    main()
