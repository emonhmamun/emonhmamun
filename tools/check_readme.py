#!/usr/bin/env python3
"""🔍 README health-checker — emonhmamun

Offline, dependency-free validator for the profile README. Used locally and
by .github/workflows/verify.yml on every push / PR. It checks:

  1. Every <img src>/<a href> URL is well-formed https and has no whitespace.
  2. Every shields.io `logo=` slug exists in simple-icons (snapshot in
     tools/data/simple-icons-slugs.txt) — unknown slugs render iconless.
  3. Every skillicons.dev icon id resolves (base names or the service's
     short-name aliases; snapshot in tools/data/skillicons-base.txt).
  4. Every shields.io github badge uses a route that exists
     (github/stars requires user+repo).
  5. All automation markers used by the updater scripts are present:
     LIVE_STATUS, DYNAMIC, activity feed.
  6. Every local asset referenced in the README exists on disk and its file
     magic matches the extension (GitHub serves raw with nosniff).

Exit code 0 = clean, 1 = problems found. `--ci` prints a GH-Actions-friendly
summary but behaves the same.
"""

import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, 'README.md')
DATA = os.path.join(ROOT, 'tools', 'data')

SKILLICONS_SHORTNAMES = {
    'js', 'ts', 'py', 'tailwind', 'vue', 'nuxt', 'go', 'cf', 'wasm',
    'postgres', 'k8s', 'next', 'mongo', 'md', 'ps', 'ai', 'pr', 'ae',
    'scss', 'sc', 'net', 'gatsbyjs', 'gql', 'vlang', 'amazonwebservices',
    'bots', 'express', 'googlecloud', 'mui', 'windi', 'unreal', 'nest',
    'ktorio', 'pwsh', 'au', 'rollup', 'rxjs', 'rxjava', 'ghactions',
    'sklearn',
}

MAGIC = {
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
    '.gif': (b'GIF87a', b'GIF89a'),
    '.svg': (b'<',),
}


def load_set(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as fh:
        return {line.strip() for line in fh if line.strip()}


def main():
    problems = []
    warns = []

    with open(README, encoding='utf-8') as fh:
        md = fh.read()

    urls = re.findall(r'(?:src|href)="([^"]+)"', md)

    # ── 1. well-formed urls ───────────────────────────────────────
    for u in urls:
        if u.startswith('#') or u.startswith('mailto:'):
            continue
        if ' ' in u:
            problems.append(f'URL contains whitespace: {u}')
        if u.startswith('http://'):
            problems.append(f'insecure http URL: {u}')
        if u.startswith('https://') and '%' not in u:
            q = urllib.parse.urlsplit(u).query
            if ' ' in q:
                problems.append(f'raw space in query of {u}')

    # ── 2. shields logo slugs ─────────────────────────────────────
    slugs = load_set(os.path.join(DATA, 'simple-icons-slugs.txt'))
    logos = sorted(set(re.findall(r'[?&]logo=([A-Za-z0-9_\-.]+)', md)))
    if slugs is None:
        warns.append('simple-icons snapshot missing — skipping logo check')
    else:
        for name in logos:
            if name.lower() not in slugs:
                problems.append(
                    f'shields logo "{name}" is not a simple-icons slug '
                    f'(badge renders without an icon)')

    # ── 3. skillicons ids ─────────────────────────────────────────
    base = load_set(os.path.join(DATA, 'skillicons-base.txt'))
    for param in re.findall(r'skillicons\.dev/icons\?i=([^"&]+)', md):
        for icon in param.split(','):
            icon = icon.strip()
            if not icon:
                continue
            if base is None:
                break
            if icon not in base and icon not in SKILLICONS_SHORTNAMES:
                problems.append(f'skillicons icon "{icon}" does not exist '
                                f'(service renders literal "undefined")')

    # ── 4. shields github routes ──────────────────────────────────
    for u in re.findall(r'https://img\.shields\.io/github/stars/([^"?]+)', md):
        if '/' not in u.strip('/'):
            problems.append('shields route github/stars/<user> is invalid — '
                            'the route requires github/stars/<user>/<repo>')

    # ── 5. automation markers ─────────────────────────────────────
    for marker in ['<!-- LIVE_STATUS_START -->', '<!-- LIVE_STATUS_END -->',
                   '<!--DYNAMIC:START-->', '<!--DYNAMIC:END-->',
                   '<!--START_SECTION:activity-->', '<!--END_SECTION:activity-->']:
        if marker not in md:
            problems.append(f'README is missing automation marker {marker}')

    # ── 6. local assets ───────────────────────────────────────────
    for rel in set(re.findall(
            r'raw\.githubusercontent\.com/emonhmamun/emonhmamun/[^"]*?/(assets/[^"?#]+)',
            md)):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            problems.append(f'referenced asset missing on disk: {rel}')
            continue
        ext = os.path.splitext(rel)[1].lower()
        with open(path, 'rb') as fh:
            head = fh.read(8)
        if ext in MAGIC and not head.startswith(MAGIC[ext]):
            problems.append(f'asset {rel}: content does not match '
                            f'extension {ext}')

    # local file references (profile-3d-contrib, assets) via relative paths
    for rel in set(re.findall(r'\bsrc="(assets/[^"]+|profile-3d-contrib/[^"]+)"',
                              md)):
        if not os.path.exists(os.path.join(ROOT, rel)):
            warns.append(f'local reference not generated yet: {rel} '
                         f'(a workflow creates it on main)')

    print('── README health check ─────────────────────────────')
    for w in warns:
        print(f'  ⚠️  {w}')
    for p in problems:
        print(f'  ❌ {p}')
    if not problems and not warns:
        print('  ✅ all checks passed')
    elif not problems:
        print('  ✅ no blocking problems')
    print(f'── {len(problems)} problem(s), {len(warns)} warning(s) ─────────')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
