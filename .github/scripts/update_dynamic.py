#!/usr/bin/env python3
"""
🌌 Dynamic README updater — emonhmamun

What it does (runs via GitHub Actions every ~30 minutes):
  1. Live Dhaka time in Bengali  → 🛰️ "রাত ১১:৪২ · শনিবার, ২২ আগস্ট ২০২৬"
  2. Rotating developer/security quote → tries ZenQuotes API,
     falls back to a curated local vault (deterministic per hour-slot,
     so the profile always has a fresh quote even if the API is down).

It rewrites everything between <!--DYNAMIC:START--> and <!--DYNAMIC:END-->
in README.md. If nothing changes, no commit is made.
"""

import json
import random
import re
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

README_PATH = "README.md"
MARK_START = "<!--DYNAMIC:START-->"
MARK_END = "<!--DYNAMIC:END-->"

# ── Bengali helpers ────────────────────────────────────────────────
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
]
BN_DAYS = [
    "সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার",
    "শুক্রবার", "শনিবার", "রবিবার",
]


def bn(n) -> str:
    """Convert numbers to Bengali numerals."""
    return str(n).translate(BN_DIGITS)


def bn_period(hour: int) -> str:
    """Bengali part-of-day word (ভোর/সকাল/দুপুর/বিকাল/সন্ধ্যা/রাত)."""
    if 4 <= hour < 6:
        return "ভোর"
    if 6 <= hour < 12:
        return "সকাল"
    if 12 <= hour < 15:
        return "দুপুর"
    if 15 <= hour < 18:
        return "বিকাল"
    if 18 <= hour < 20:
        return "সন্ধ্যা"
    return "রাত"


def dhaka_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Dhaka"))


def time_line(now: datetime) -> str:
    period = bn_period(now.hour)
    h12 = now.hour % 12 or 12
    minute = f"{now.minute:02d}"
    return f"{period} {bn(h12)}:{bn(minute)}"


def date_line(now: datetime) -> str:
    day = BN_DAYS[now.weekday()]
    return f"{day}, {bn(now.day)} {BN_MONTHS[now.month - 1]} {bn(now.year)}"


# ── Quotes ─────────────────────────────────────────────────────────
LOCAL_VAULT = [
    ("Every system I build starts as a question.", "Emon H. Mamun"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Given enough eyeballs, all bugs are shallow.", "Linus's Law"),
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("Programs must be written for people to read.", "Harold Abelson"),
    ("Security is a process, not a product.", "Bruce Schneier"),
    ("The only truly secure system is one that is powered off.", "Gene Spafford"),
    ("Amateurs hack systems, professionals hack people.", "Bruce Schneier"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Premature optimization is the root of all evil.", "Donald Knuth"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("The best error message is the one that never shows up.", "Thomas Fuchs"),
    ("Deleted code is debugged code.", "Jeff Sickel"),
    ("The most disastrous thing you can ever learn is your first programming language.", "Alan Kay"),
    ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
    ("In theory there is no difference between theory and practice. In practice there is.", "Yogi Berra"),
    ("If you don't fail at least 90% of the time, you're not aiming high enough.", "Alan Kay"),
    ("The function of good software is to make the complex appear simple.", "Grady Booch"),
    ("An API that isn't comprehensible isn't usable.", "Steve Craggs"),
    ("Automation is cost center until it saves you at 3 AM.", "DevOps Lore"),
    ("Trust, but verify. Then automate the verification.", "Security Wisdom"),
    ("The perimeter you build should watch itself.", "Emon H. Mamun"),
    ("Curiosity is the ultimate debugger.", "Emon H. Mamun"),
    ("Any sufficiently advanced hack is indistinguishable from logging in.", "Techno-Folk Theorem"),
    ("The cloud is just someone else's computer — secure accordingly.", "Modern Proverb"),
    ("Repetition is the mother of automation.", "Workflow Wisdom"),
]


def clean(text: str) -> str:
    """Make a quote markdown-safe."""
    text = text.strip()
    text = text.replace("\n", " ").replace('"', "'")
    return re.sub(r"\s+", " ", text)


def fetch_quote(now: datetime):
    """Try ZenQuotes API; fall back to the local vault (stable per hour)."""
    try:
        req = urllib.request.Request(
            "https://zenquotes.io/api/random",
            headers={"User-Agent": "Mozilla/5.0 (dynamic-readme-bot)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        quote, author = clean(data[0]["q"]), clean(data[0]["a"])
        if quote and author:
            return quote, author, "ZenQuotes"
    except Exception as exc:  # noqa: BLE001 — any failure → fallback
        print(f"ZenQuotes unavailable ({exc}); using local vault.")
    rng = random.Random(now.strftime("%Y-%m-%d-%H"))
    quote, author = rng.choice(LOCAL_VAULT)
    return quote, author, "Local Vault"


# ── README rewrite ─────────────────────────────────────────────────
def build_block(now: datetime) -> str:
    quote, author, source = fetch_quote(now)
    return f"""{MARK_START}
<div align="center">

<img src="https://img.shields.io/badge/%F0%9F%9B%B0%EF%B8%8F_LIVE_FROM_DHAKA-GMT%2B6-7C3AED?style=flat-square&labelColor=0d1117" alt="Live from Dhaka" />
<img src="https://img.shields.io/badge/%F0%9F%92%AC_THOUGHT_OF_THE_MOMENT-refreshes_automatically-22D3EE?style=flat-square&labelColor=0d1117" alt="Quote" />

🛰️ **`{time_line(now)}` · `{date_line(now)}`** *(GMT+6 · auto-refreshed every 30 min by GitHub Actions)*

> 💬 *"{quote}"*
> — **{author}** <sub>· via {source}</sub>

</div>
{MARK_END}"""


def main() -> int:
    try:
        with open(README_PATH, encoding="utf-8") as fh:
            readme = fh.read()
    except FileNotFoundError:
        print(f"ERROR: {README_PATH} not found.")
        return 1

    if MARK_START not in readme or MARK_END not in readme:
        print(f"ERROR: markers {MARK_START}/{MARK_END} missing in {README_PATH}.")
        return 1

    block = build_block(dhaka_now())
    pattern = re.compile(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END), re.DOTALL
    )
    new_readme = pattern.sub(lambda _: block, readme, count=1)

    if new_readme == readme:
        print("No dynamic changes — nothing to update.")
        return 0

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_readme)
    print("Dynamic block updated ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
