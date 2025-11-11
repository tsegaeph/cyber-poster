#!/usr/bin/env python3

import os
import random
import requests
import feedparser
from datetime import datetime
from dotenv import load_dotenv

# Load secrets from environment (GitHub Actions)
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("MESSAGE_THREAD_ID")  # For the "News" topic
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")
POSTED_FILE = os.getenv("POSTED_FILE", "posted_urls.txt")

BASE_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Ensure posted_urls.txt exists
if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

# Load previously posted URLs
with open(POSTED_FILE, "r") as f:
    posted_urls = set(line.strip() for line in f if line.strip())

def log(message):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {message}")

def fetch_news():
    """Fetch all news from the RSS feeds and return only new (unposted) ones."""
    new_items = []
    for feed_url in RSS_FEEDS:
        feed_url = feed_url.strip()
        if not feed_url:
            continue
        parsed = feedparser.parse(feed_url)
        log(f"Fetched {len(parsed.entries)} items from {feed_url}")
        for entry in parsed.entries:
            url = entry.get("link")
            if not url or url in posted_urls:
                continue  # Skip duplicates
            title = entry.get("title", "No title")
            summary = entry.get("summary", "")[:400]
            new_items.append({"title": title, "url": url, "summary": summary})
    return new_items

def send_telegram_message(title, summary, url):
    """Send a message to Telegram (either to general or a topic)."""
    message = f"<b>{title}</b>\n\n{summary}\n\n<a href='{url}'>Read more</a>"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    if THREAD_ID:
        payload["message_thread_id"] = int(THREAD_ID)
    res = requests.post(f"{BASE_API}/sendMessage", json=payload)
    res.raise_for_status()
    return res.json()

def save_posted(url):
    """Add a posted URL to the record file."""
    posted_urls.add(url)
    with open(POSTED_FILE, "a") as f:
        f.write(url + "\n")

def main():
    log("Fetching latest articles...")
    news_items = fetch_news()

    if not news_items:
        log("⚠️ No new unique articles found today — skipping post.")
        return

    # Post only ONE article per run (and skip duplicates automatically)
    item = random.choice(news_items)

    try:
        send_telegram_message(item["title"], item["summary"], item["url"])
        save_posted(item["url"])
        log(f"✅ Posted: {item['title']}")
    except Exception as e:
        log(f"⚠️ Failed to post {item['title']}: {e}")

if __name__ == "__main__":
    main()
