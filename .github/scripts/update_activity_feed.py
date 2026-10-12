"""📡 Latest Activity feed — emonhmamun

Self-hosted replacement for the (broken) jamesgeorge007/github-activity-readme
third-party action: pulls the user's latest public GitHub events from the
REST API and renders them as a markdown list between the markers

    <!--START_SECTION:activity-->
    <!--END_SECTION:activity-->

in README.md. No Node.js, no deprecated action, and a graceful fallback line
when the API is quiet or unreachable. Exits 0 with "no changes" when the feed
content would be identical, so CI does not loop.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

README_FILE = 'README.md'
MARK_START = '<!--START_SECTION:activity-->'
MARK_END = '<!--END_SECTION:activity-->'
GITHUB_USER = 'emonhmamun'
MAX_LINES = 6
TZ = timezone(timedelta(hours=6))  # Asia/Dhaka


def gh_get(path, token=None):
    req = urllib.request.Request(
        f'https://api.github.com{path}',
        headers={
            'User-Agent': 'emonhmamun-readme-bot',
            'Accept': 'application/vnd.github+json',
            **({'Authorization': f'Bearer {token}'} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fmt_when(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(TZ)
        return dt.strftime('%d %b %Y, %I:%M %p')
    except Exception:  # noqa: BLE001
        return 'recently'


def render_event(ev):
    """One markdown bullet per public event; None when uninteresting."""
    etype = ev.get('type')
    repo = ev.get('repo', {}).get('name', '').split('/', 1)[-1]
    payload = ev.get('payload', {})
    when = fmt_when(ev.get('created_at', ''))

    if etype == 'PushEvent':
        n = payload.get('size', 1)
        word = 'commit' if n == 1 else 'commits'
        return f"🕒 Pushed **{n} {word}** to `{repo}` · _{when}_"
    if etype == 'CreateEvent':
        kind = payload.get('ref_type', 'repository')
        ref = payload.get('ref') or ''
        target = f"`{ref}` {kind}" if ref else f"a new {kind}"
        return f"🌱 Created {target} in `{repo}` · _{when}_"
    if etype == 'ReleaseEvent':
        tag = payload.get('release', {}).get('tag_name', 'latest')
        return f"🚀 Released **{tag}** of `{repo}` · _{when}_"
    if etype == 'PullRequestEvent':
        act = payload.get('action', 'updated')
        num = payload.get('number', '')
        return f"🔀 {act.title()} PR **#{num}** in `{repo}` · _{when}_"
    if etype == 'IssuesEvent':
        act = payload.get('action', 'updated')
        num = payload.get('issue', {}).get('number', '')
        return f"🐛 {act.title()} issue **#{num}** in `{repo}` · _{when}_"
    if etype == 'WatchEvent':
        return f"⭐ Starred `{repo}` · _{when}_"
    if etype == 'ForkEvent':
        return f"🍴 Forked `{repo}` · _{when}_"
    if etype == 'PublicEvent':
        return f"🎉 Made `{repo}` public · _{when}_"
    return None


def build_feed(token=None):
    lines = []
    try:
        events = gh_get(f'/users/{GITHUB_USER}/events/public?per_page=30', token)
    except Exception as exc:  # noqa: BLE001
        print(f'activity feed: GitHub API unreachable ({exc})')
        events = []
    for ev in events or []:
        line = render_event(ev)
        if line and line not in lines:
            lines.append(line)
        if len(lines) >= MAX_LINES:
            break
    if not lines:
        lines = ["🌙 Quiet period on the wire — the perimeter is calm. "
                 "New pushes, releases & PRs will appear here automatically."]
    body = '\n'.join(f'- {l}' for l in lines)
    return (f'{MARK_START}\n\n{body}\n\n'
            f'<sub>🔄 auto-refreshed from the GitHub Events API every 6 hours'
            f' by `.github/workflows/update-readme.yml`</sub>\n\n{MARK_END}')


def main():
    if not os.path.exists(README_FILE):
        print(f'ERROR: {README_FILE} not found')
        return 1
    with open(README_FILE, encoding='utf-8') as fh:
        readme = fh.read()
    if MARK_START not in readme or MARK_END not in readme:
        print(f'ERROR: markers {MARK_START} / {MARK_END} missing')
        return 1

    block = build_feed(os.environ.get('GITHUB_TOKEN') or None)
    pattern = re.compile(re.escape(MARK_START) + r'.*?' + re.escape(MARK_END),
                         re.DOTALL)
    new_readme = pattern.sub(lambda _: block, readme, count=1)
    if new_readme == readme:
        print('Activity feed already up to date — no changes.')
        return 0
    with open(README_FILE, 'w', encoding='utf-8') as fh:
        fh.write(new_readme)
    print('Activity feed updated ✅')
    return 0


if __name__ == '__main__':
    sys.exit(main())
