import json
import os
import re
from datetime import datetime, timedelta, timezone

ACTIVITY_FILE = 'stats/activity.json'
README_FILE = 'README.md'
TZ = timezone(timedelta(hours=6))

def now():
    return datetime.now(TZ)

def load_activity():
    if os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE) as f:
            return json.load(f)
    return {
        "lastActivity": "", "currentTask": "ready",
        "sessionsToday": 0, "sessionsThisWeek": 0,
        "currentStreak": 0, "totalHours": 0,
        "totalSessions": 0, "lastUpdated": "",
        "timezone": "Asia/Dhaka", "lastDate": "",
        "lastWeekNumber": 0, "activityLog": []
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
        diff = now() - dt
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return "Just_Now"
        elif minutes < 60:
            return f"{minutes}m_ago"
        elif minutes < 1440:
            return f"{minutes // 60}h_ago"
        else:
            return f"{minutes // 1440}d_ago"
    except:
        return "Unknown"

def get_week_number(dt):
    return dt.isocalendar()[1]

def calculate_streak(log):
    if not log:
        return 0
    dates = set()
    for entry in log[-200:]:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            dates.add(dt.strftime('%Y-%m-%d'))
        except:
            pass
    if not dates:
        return 0
    streak = 0
    check = now()
    while True:
        ds = check.strftime('%Y-%m-%d')
        if ds in dates:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak

def get_greeting():
    h = now().hour
    if 5 <= h < 12:
        return "Good_Morning"
    elif 12 <= h < 17:
        return "Good_Afternoon"
    elif 17 <= h < 21:
        return "Good_Evening"
    else:
        return "Good_Night"

def get_status_info(data):
    last = relative_time(data.get('lastActivity', ''))
    if last == "Never":
        return "WAITING", "lightgrey"
    elif last == "Just_Now" or (last.endswith('m_ago') and int(last.split('m')[0]) <= 30):
        return "ACTIVE", "brightgreen"
    elif last.endswith('h_ago') and int(last.split('h')[0]) <= 6:
        return "RECENT", "yellow"
    else:
        return "IDLE", "red"

def badge(label, value, color, style="for-the-badge"):
    return f'<img src="https://img.shields.io/badge/{label}-{value}-{color}?style={style}&labelColor=0d1117" alt="{label}" />'

def generate_status_html(data):
    status, status_color = get_status_info(data)
    last_active = relative_time(data.get('lastActivity', ''))
    greeting = get_greeting()

    task_labels = {
        'coding': 'Coding', 'security-research': 'Security_Research',
        'automation': 'Automation', 'system-building': 'System_Building',
        'debugging': 'Debugging', 'learning': 'Learning',
        'ctf': 'CTF_Challenge', 'review': 'Code_Review', 'ready': 'Ready'
    }
    task = data.get('currentTask', 'ready')
    task_label = task_labels.get(task, 'Working')

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
</tr></table>

<table><tr>
<td>{badge(greeting, "from_Bangladesh", "F97316")}</td>
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
        print("README updated")
        return True
    print("No README changes needed")
    return False

def main():
    data = load_activity()
    event = os.environ.get('EVENT_NAME', 'schedule')
    activity_type = os.environ.get('ACTIVITY_TYPE', '')
    duration = int(os.environ.get('DURATION_MINUTES', '0') or '0')

    now_dt = now()
    today_str = now_dt.strftime('%Y-%m-%d')
    current_week = get_week_number(now_dt)

    # Reset daily counter if new day
    if data.get('lastDate', '') != today_str:
        data['sessionsToday'] = 0
        data['lastDate'] = today_str

    # Reset weekly counter if new week
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
        log.append({
            "type": activity_type,
            "duration": duration,
            "timestamp": now_dt.isoformat()
        })
        data['activityLog'] = log[-200:]
        print(f"Session logged: {activity_type} for {duration}min")
    elif event == 'schedule':
        print("Scheduled maintenance: counters reset if needed")

    data['currentStreak'] = calculate_streak(data.get('activityLog', []))
    data['lastUpdated'] = now_dt.isoformat()

    save_activity(data)

    html = generate_status_html(data)
    update_readme(html)

    print(f"Done. Sessions: {data['totalSessions']}, Streak: {data['currentStreak']}d, Hours: {data['totalHours']}")

if __name__ == '__main__':
    main()
