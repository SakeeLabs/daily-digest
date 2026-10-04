#!/usr/bin/env python3
"""Dev Radar collector: repos newly added to curated GitHub lists, found by diffing each list
between a base commit (before the window) and HEAD. Uses only `git` (no GitHub API needed).
Usage: python3 collect.py [hours=168] > out.json
"""
import subprocess, re, json, sys, os, tempfile, datetime

HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 168
LISTS = {
    'punkpeye/awesome-mcp-servers': 'MCP servers',
    'hesreallyhim/awesome-claude-code': 'Claude Code tools',
    'VoltAgent/awesome-agent-skills': 'Agent skills',
    'travisvn/awesome-claude-skills': 'Claude skills',
    'ComposioHQ/awesome-claude-skills': 'Claude skills',
    'e2b-dev/awesome-ai-agents': 'AI agents',
    'Shubhamsaboo/awesome-llm-apps': 'LLM apps',
    'anthropics/skills': 'Official Anthropic skills',
    'modelcontextprotocol/servers': 'Official MCP servers',
}
LINK = re.compile(r'\[([^\]]{1,120})\]\((https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+))[^)]*\)')
SKIP_OWNERS = {'punkpeye', 'hesreallyhim', 'voltagent', 'travisvn', 'composiohq', 'e2b-dev', 'shubhamsaboo', 'sindresorhus'}

def git(*a, cwd=None, timeout=240):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, timeout=timeout)

def entries(cwd, rev):
    """repo key -> (display name, cleaned description) for every GitHub link in markdown files at rev."""
    out = {}
    files = git('ls-tree', '-r', '--name-only', rev, cwd=cwd).stdout.split()
    for f in files:
        if not f.lower().endswith('.md'):
            continue
        txt = git('show', f'{rev}:{f}', cwd=cwd).stdout
        for line in txt.splitlines():
            for m in LINK.finditer(line):
                name, url, owner, rp = m.groups()
                rp = rp.removesuffix('.git').rstrip('.')
                if owner.lower() in SKIP_OWNERS or rp.lower() in ('issues', 'pulls', 'blob', 'tree'):
                    continue
                key = f'{owner}/{rp}'
                if key in out:
                    continue
                rest = line[m.end():]
                rest = re.sub(r'\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\)|\[\]\([^)]*\)', '', rest)
                rest = re.sub(r'[\U0001F000-\U0001FAFF☀-➿️]', '', rest)
                rest = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', rest)
                rest = re.sub(r'#\u20e3|[\u20e3\u200d]', '', rest)
                rest = re.sub(r'<[^>]+>|[`*_|]', '', rest).strip(' -–—:\t')
                out[key] = (name.strip(), rest[:240], f)
    return out

work = tempfile.mkdtemp()
now = datetime.datetime.now(datetime.timezone.utc)
since = now - datetime.timedelta(hours=HOURS)
res = {'generated': now.isoformat(), 'window_hours': HOURS, 'lists': [], 'added': []}
seen = set()
for repo, label in LISTS.items():
    d = os.path.join(work, repo.replace('/', '__'))
    days = HOURS // 24 + 5
    r = git('clone', '-q', '--filter=blob:none', f'--shallow-since={days} days ago', f'https://github.com/{repo}.git', d)
    if r.returncode != 0:
        r = git('clone', '-q', '--filter=blob:none', '--depth', '200', f'https://github.com/{repo}.git', d)
    if r.returncode != 0:
        res['lists'].append({'repo': repo, 'label': label, 'error': r.stderr.strip()[:200]})
        continue
    base = git('rev-list', '-1', f'--before={since.isoformat()}', 'HEAD', cwd=d).stdout.strip()
    subjects = git('log', f'--since={since.isoformat()}', '--first-parent', '--format=%cI %s', cwd=d).stdout.strip().splitlines()
    if not base:  # shallow history doesn't reach the window start: deepen once
        git('fetch', '-q', '--deepen=300', cwd=d)
        base = git('rev-list', '-1', f'--before={since.isoformat()}', 'HEAD', cwd=d).stdout.strip()
    if not subjects:
        res['lists'].append({'repo': repo, 'label': label, 'commits': 0, 'new': 0, 'subjects': []})
        continue
    head_e = entries(d, 'HEAD')
    base_e = entries(d, base) if base else {}
    n = 0
    for key, (name, desc, f) in head_e.items():
        if key in base_e or key.lower() in seen:
            continue
        seen.add(key.lower()); n += 1
        res['added'].append({'repo': key, 'url': f'https://github.com/{key}', 'name': name, 'desc': desc,
                             'source': repo, 'category': label, 'file': f})
    res['lists'].append({'repo': repo, 'label': label, 'commits': len(subjects), 'new': n,
                         'base': base[:10], 'subjects': subjects[:15]})
json.dump(res, sys.stdout, indent=1, ensure_ascii=False)
