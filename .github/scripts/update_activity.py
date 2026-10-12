"""🛰️ Live Coding Status updater — emonhmamun

Runs via .github/workflows/track-activity.yml (daily + manual dispatch).
It keeps two things honest on the profile README:

  1. Session bookkeeping (manual "I'm coding" dispatches) stored in
     stats/activity.json.
  2. Real GitHub signals (followers / public repos / all-time commits)
     pulled from the public REST API so the status block is never a
     wall of zeros.

It rewrites everything between <!-- LIVE_STATUS_START --> and
<!-- LIVE_STATUS_END --> in README.md. No change → no rewrite.
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

ACTIVITY_FILE = 'stats/activity.json'
README_FILE = 'README.md'
GITHUB_USER = 'emonhmamun'
TZ = timezone(timedelta(hours=6))  # Asia/Dhaka

API = 'https://api.github.com'


def now():
    return datetime.now(TZ)


def gh_get(path, token=None):
    """GET a GitHub REST endpoint; return parsed JSON or None on any error."""
    req = urllib.request.Request(
        f'{API}{path}',
        headers={
            'User-Agent': 'emonhmamun-readme-bot',
            'Accept': 'application/vnd.github+json',
            **({'Authorization': f'Bearer {token}'} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001 — API hiccups must never kill the run
        print(f'github api {path} unavailable: {exc}')
        return None


def load_activity():
    if os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE) as f:
            return json.load(f)
    return {
        "lastActivity": "", "currentTask": "ready",
        "sessionsToday": 0, "sessionsThisWeek": 0,
        "currentStreak": 0, "totalHours": 0, "totalSessions": 0,
        "lastUpdated": "", "timezone": "Asia/Dhaka", "lastDate": "",
        "lastWeekNumber": 0, "activityLog": [],
    }


def save_activity(data):
    os.makedirs('stats', exist_ok=True)
    with open(ACTIVITY_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def relative_time(dt_str):
    if not dt_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        minutes = int((now() - dt).total_seconds() / 60)
        if minutes < 1:
            return "Just_Now"
        if minutes < 60:
            return f"{minutes}m_ago"
        if minutes < 1440:
            return f"{minutes // 60}h_ago"
        return f"{minutes // 1440}d_ago"
    except Exception:  # noqa: BLE001
        return "Unknown"


def calculate_streak(log):
    """Consecutive active days ending today; if today has no entry yet the
    streak may still be alive from yesterday (standard streak semantics)."""
    dates = set()
    for entry in log[-200:]:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            dates.add(dt.strftime('%Y-%m-%d'))
        except Exception:  # noqa: BLE001
            continue
    if not dates:
        return 0
    check = now()
    if check.strftime('%Y-%m-%d') not in dates:
        check -= timedelta(days=1)  # today not logged yet — count up to yesterday
    streak = 0
    while check.strftime('%Y-%m-%d') in dates:
        streak += 1
        check -= timedelta(days=1)
    return streak


def get_greeting():
    h = now().hour
    if 5 <= h < 12:
        return "Good_Morning"
    if 12 <= h < 17:
        return "Good_Afternoon"
    if 17 <= h < 21:
        return "Good_Evening"
    return "Good_Night"


def get_status_info(data):
    last = relative_time(data.get('lastActivity', ''))
    if last == "Never":
        return "WAITING", "lightgrey"
    if last == "Just_Now" or (last.endswith('m_ago') and int(last.split('m')[0]) <= 30):
        return "ACTIVE", "brightgreen"
    if last.endswith('h_ago') and int(last.split('h')[0]) <= 6:
        return "RECENT", "yellow"
    return "IDLE", "red"


def fetch_github_signals(token=None):
    """Real, public GitHub numbers so the dashboard is alive even before any
    manual session is logged. Each key is None when the API is unreachable."""
    sig = {'followers': None, 'repos': None, 'commits': None}
    user = gh_get(f'/users/{GITHUB_USER}', token)
    if user:
        sig['followers'] = user.get('followers')
        sig['repos'] = user.get('public_repos')
    search = gh_get(f'/search/commits?q=author:{GITHUB_USER}', token)
    if search and 'total_count' in search:
        sig['commits'] = search['total_count']
    return sig


def badge(label, value, color, style="for-the-badge"):
    return (f'<img src="https://img.shields.io/badge/{label}-{value}-{color}'
            f'?style={style}&labelColor=0d1117" alt="{label}" />')


def generate_status_html(data, sig):
    status, status_color = get_status_info(data)
    last_active = relative_time(data.get('lastActivity', ''))
    greeting = get_greeting()

    task_labels = {
        'coding': 'Coding', 'security-research': 'Security_Research',
        'automation': 'Automation', 'system-building': 'System_Building',
        'debugging': 'Debugging', 'learning': 'Learning',
        'ctf': 'CTF_Challenge', 'review': 'Code_Review', 'ready': 'Ready',
    }
    task_label = task_labels.get(data.get('currentTask', 'ready'), 'Working')

    last_color = status_color if last_active != "Never" else "lightgrey"
    html = f'''<table><tr>
<td>{badge("Status", status, status_color)}</td>
<td>{badge("Last_Active", last_active, last_color)}</td>
</tr></table>

<table><tr>
<td>{badge("Current_Task", task_label, "7C3AED")}</td>
<td>{badge("Sessions_Today", str(data.get("sessionsToday", 0)), "22D3EE")}</td>
</tr></table>

<table><tr>
<td>{badge("Current_Streak", str(data.get("currentStreak", 0)) + "_days", "EC4899")}</td>
<td>{badge("This_Week", str(data.get("sessionsThisWeek", 0)) + "_sessions", "A855F7")}</td>
</tr></table>

<table><tr>
<td>{badge("Total_Hours", str(data.get("totalHours", 0)), "7C3AED")}</td>
<td>{badge("Total_Sessions", str(data.get("totalSessions", 0)), "22D3EE")}</td>
</tr></table>'''

    # ── Real GitHub signals (graceful when the API is down) ──
    gh_cells = []
    if sig['commits'] is not None:
        gh_cells.append(f'<td>{badge("All_Time_Commits", str(sig["commits"]), "7C3AED")}</td>')
    if sig['repos'] is not None:
        gh_cells.append(f'<td>{badge("Public_Repos", str(sig["repos"]), "22D3EE")}</td>')
    if sig['followers'] is not None:
        gh_cells.append(f'<td>{badge("Followers", str(sig["followers"]), "EC4899")}</td>')
    if gh_cells:
        html += "\n\n<table><tr>\n" + "\n".join(gh_cells) + "\n</tr></table>"

    html += f'''

<table><tr>
<td>{badge("%F0%9F%91%8B_" + greeting, "from_Bangladesh", "F97316")}</td>
<td>{badge("Updated", relative_time(data.get("lastUpdated", "")), "1f2937")}</td>
</tr></table>'''
    return html


def update_readme(html):
    if not os.path.exists(README_FILE):
        print("README not found")
        return False
    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    marker_start = '<!-- LIVE_STATUS_START -->'
    marker_end = '<!-- LIVE_STATUS_END -->'
    if marker_start not in content or marker_end not in content:
        print("Markers not found in README")
        return False
    pattern = re.escape(marker_start) + r'.*?' + re.escape(marker_end)
    new_section = f'{marker_start}\n{html}\n{marker_end}'
    new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    if new_content != content:
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("README live-status block updated")
        return True
    print("No README changes needed")
    return False


def main():
    data = load_activity()
    event = os.environ.get('EVENT_NAME', 'schedule')
    activity_type = os.environ.get('ACTIVITY_TYPE', '')
    duration = int(os.environ.get('DURATION_MINUTES', '0') or '0')
    token = os.environ.get('GITHUB_TOKEN') or None

    now_dt = now()
    today_str = now_dt.strftime('%Y-%m-%d')
    current_week = now_dt.isocalendar()[1]

    if data.get('lastDate', '') != today_str:
        data['sessionsToday'] = 0
        data['lastDate'] = today_str

    if data.get('lastWeekNumber', 0) != current_week:
        data['sessionsThisWeek'] = 0
        data['lastWeekNumber'] = current_week

    if event == 'workflow_dispatch' and activity_type:
        data['lastActivity'] = now_dt.isoformat()
        data['currentTask'] = activity_type
        data['sessionsToday'] = data.get('sessionsToday', 0) + 1
        data['sessionsThisWeek'] = data.get('sessionsThisWeek', 0) + 1
        data['totalSessions'] = data.get('totalSessions', 0) + 1
        data['totalHours'] = round(data.get('totalHours', 0) + duration / 60, 1)
        log = data.get('activityLog', [])
        log.append({"type": activity_type, "duration": duration,
                    "timestamp": now_dt.isoformat()})
        data['activityLog'] = log[-200:]
        print(f"Session logged: {activity_type} for {duration}min")
    elif event == 'schedule':
        print("Scheduled maintenance: counters reset if needed")

    data['currentStreak'] = calculate_streak(data.get('activityLog', []))
    data['lastUpdated'] = now_dt.isoformat()

    save_activity(data)

    sig = fetch_github_signals(token)
    html = generate_status_html(data, sig)
    update_readme(html)

    print(f"Done. Sessions: {data['totalSessions']}, Streak: "
          f"{data['currentStreak']}d, Hours: {data['totalHours']}, GH: {sig}")


if __name__ == '__main__':
    main()
