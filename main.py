import os
import json
import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz

from dotenv import load_dotenv
load_dotenv()

import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

import discord
from discord.ext import tasks

# ------------------- Config -------------------
TZ = pytz.timezone("Asia/Kolkata")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("HACKATHON_CHANNEL_ID", "0"))
INTERVAL_HOURS = float(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
MAX_ITEMS = int(os.getenv("MAX_ITEMS_PER_CYCLE", "6"))
SOURCES_ENABLED = [
    s.strip().lower()
    for s in os.getenv(
        "SOURCES_ENABLED", "hackerearth,devpost,techgig,devfolio,unstop,mlh"
    ).split(",")
    if s.strip()
]

STATE_FILE = "posted_hackathons.json"

HEADERS = {
    "User-Agent": "india-hackathons-bot/2.0 (+student project)"
}


# ------------------- Utilities -------------------
def now_ist() -> datetime:
    return datetime.now(tz=TZ)


def load_state() -> Dict[str, bool]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: Dict[str, bool]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_india_text(text: str) -> bool:
    if not text:
        return False
    text_l = text.lower()
    india_terms = [
        "india",
        "bangalore",
        "bengaluru",
        "mumbai",
        "delhi",
        "pune",
        "hyderabad",
        "chennai",
        "kolkata",
        "ahmedabad",
        "jaipur",
        "gurgaon",
        "noida",
        "kerala",
        "goa",
        "lucknow",
    ]
    return any(term in text_l for term in india_terms)


def parse_date_guess(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        dt = dateparser.parse(s, dayfirst=True)
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = TZ.localize(dt)
        else:
            dt = dt.astimezone(TZ)
        return dt.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return None


# ------------------- Scrapers -------------------
async def scrape_hackerearth(session):
    url = "https://www.hackerearth.com/challenges/hackathon/?country=india"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            html = await resp.text()
        soup = BeautifulSoup(html, "lxml")
        for c in soup.select(".challenge-card-modern, .challenge-card"):
            title_el = c.select_one("h3, .challenge-card__title")
            link_el = c.find("a", href=True)
            org_el = c.select_one(".company-name, .challenge-card-modern__company")
            meta_el = c.select_one(".challenge-card__details")
            title = clean(title_el.get_text()) if title_el else None
            link = link_el["href"] if link_el else None
            if link and link.startswith("/"):
                link = "https://www.hackerearth.com" + link
            if not (title and link):
                continue
            items.append(
                {
                    "title": title,
                    "host": clean(org_el.get_text()) if org_el else "HackerEarth",
                    "when": clean(meta_el.get_text()) if meta_el else "",
                    "location": "India",
                    "url": link,
                    "source": "HackerEarth",
                }
            )
    except Exception as e:
        print("hackerearth error:", e)
    return items


async def scrape_devpost(session):
    url = "https://devpost.com/hackathons?search=india&sort_by=recent"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            soup = BeautifulSoup(await resp.text(), "lxml")
        for li in soup.select(".hackathon-tile, .challenge-listing"):
            title_el = li.select_one(".title, h3")
            link_el = li.find("a", href=True)
            org_el = li.select_one(".organizer, .subtitle")
            date_el = li.select_one(".submission-period, .dates")
            title = clean(title_el.get_text()) if title_el else None
            link = link_el["href"] if link_el else None
            if link and link.startswith("/"):
                link = "https://devpost.com" + link
            if not (title and link):
                continue
            items.append(
                {
                    "title": title,
                    "host": clean(org_el.get_text()) if org_el else "Devpost",
                    "when": clean(date_el.get_text()) if date_el else "",
                    "location": "India / Online",
                    "url": link,
                    "source": "Devpost",
                }
            )
    except Exception as e:
        print("devpost error:", e)
    return items


async def scrape_techgig(session):
    url = "https://www.techgig.com/challenge"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            soup = BeautifulSoup(await resp.text(), "lxml")
        for a in soup.select("a[href*='/challenge/']"):
            title = clean(a.get_text())
            if "hackathon" not in title.lower() and "challenge" not in title.lower():
                continue
            link = a["href"]
            if link.startswith("/"):
                link = "https://www.techgig.com" + link
            items.append(
                {
                    "title": title,
                    "host": "TechGig",
                    "when": "",
                    "location": "India / Online",
                    "url": link,
                    "source": "TechGig",
                }
            )
    except Exception as e:
        print("techgig error:", e)
    return items


async def scrape_devfolio(session):
    url = "https://devfolio.co/hackathons"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            soup = BeautifulSoup(await resp.text(), "lxml")
        for card in soup.select("a[href*='/hackathons/']"):
            title = clean(card.get_text())
            link = card["href"]
            if link.startswith("/"):
                link = "https://devfolio.co" + link
            if not (title and link):
                continue
            if not is_india_text(title):
                continue
            items.append(
                {
                    "title": title,
                    "host": "Devfolio",
                    "when": "",
                    "location": "India",
                    "url": link,
                    "source": "Devfolio",
                }
            )
    except Exception as e:
        print("devfolio error:", e)
    return items


async def scrape_unstop(session):
    url = "https://unstop.com/hackathons"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            soup = BeautifulSoup(await resp.text(), "lxml")
        for card in soup.select("a.event-card"):
            title = clean(card.get_text())
            link = card["href"]
            if link.startswith("/"):
                link = "https://unstop.com" + link
            if not is_india_text(title):
                continue
            items.append(
                {
                    "title": title,
                    "host": "Unstop",
                    "when": "",
                    "location": "India",
                    "url": link,
                    "source": "Unstop",
                }
            )
    except Exception as e:
        print("unstop error:", e)
    return items


async def scrape_mlh(session):
    url = "https://mlh.io/seasons/2025/events"
    items = []
    try:
        async with session.get(url, headers=HEADERS) as resp:
            soup = BeautifulSoup(await resp.text(), "lxml")
        for card in soup.select(".event-wrapper"):
            title_el = card.select_one("h3")
            link_el = card.find("a", href=True)
            loc_el = card.select_one(".event-location")
            when_el = card.select_one(".event-date")
            title = clean(title_el.get_text()) if title_el else None
            link = link_el["href"] if link_el else None
            loc = clean(loc_el.get_text()) if loc_el else ""
            if not (title and link):
                continue
            if not is_india_text(loc):
                continue
            items.append(
                {
                    "title": title,
                    "host": "MLH",
                    "when": clean(when_el.get_text()) if when_el else "",
                    "location": loc,
                    "url": link,
                    "source": "MLH",
                }
            )
    except Exception as e:
        print("mlh error:", e)
    return items


SCRAPER_FUNCS = {
    "hackerearth": scrape_hackerearth,
    "devpost": scrape_devpost,
    "techgig": scrape_techgig,
    "devfolio": scrape_devfolio,
    "unstop": scrape_unstop,
    "mlh": scrape_mlh,
}

# ------------------- Discord Bot -------------------
intents = discord.Intents.none()
bot = discord.Client(intents=intents)


def format_embed(item: Dict[str, Any]) -> discord.Embed:
    embed = discord.Embed(
        title=item["title"],
        url=item["url"],
        description=f"**Host:** {item.get('host','Unknown')}\n"
        f"**When:** {item.get('when','TBA')}\n"
        f"**Location:** {item.get('location','Unknown')}",
    )
    embed.set_footer(text=f"Source: {item['source']} • {now_ist().strftime('%d %b %Y, %I:%M %p')}")
    return embed


async def gather_items():
    out = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for src in SOURCES_ENABLED:
            fn = SCRAPER_FUNCS.get(src)
            if fn:
                try:
                    out.extend(await fn(session))
                except Exception as e:
                    print(f"{src} error:", e)
    seen = set()
    uniq = []
    for i in out:
        if i["url"] not in seen:
            uniq.append(i)
            seen.add(i["url"])
    return uniq


@tasks.loop(hours=INTERVAL_HOURS)
async def cycle():
    await bot.wait_until_ready()
    ch = bot.get_channel(CHANNEL_ID)
    if not ch:
        print("Channel not found")
        return
    state = load_state()
    items = await gather_items()
    posted = 0
    for item in items:
        if state.get(item["url"]):
            continue
        try:
            await ch.send(embed=format_embed(item))
            state[item["url"]] = True
            posted += 1
            if posted >= MAX_ITEMS:
                break
            await asyncio.sleep(2)
        except Exception as e:
            print("send error:", e)
    save_state(state)
    print(f"Posted {posted} items")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    if not cycle.is_running():
        cycle.start()


if __name__ == "__main__":
    if not DISCORD_TOKEN or CHANNEL_ID == 0:
        raise SystemExit("Missing DISCORD_TOKEN or HACKATHON_CHANNEL_ID")
    bot.run(DISCORD_TOKEN)
