import os, re, hashlib, html, logging
from datetime import datetime, timezone, timedelta, date
from email.utils import parsedate_to_datetime

import feedparser
import requests

from feeds import FEEDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("radar")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
REST = f"{SUPABASE_URL}/rest/v1"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


NOW = datetime.now(timezone.utc)

# Transparent starter taxonomy. Expand and tune after reviewing real-world classifications.
CLUSTERS = [
    ("ai-agents", "AI Agents & AI Culture", "AI", ["ai agent", "ai agents", "agentic", "autonomous agent", "chatbot", "artificial intelligence", "generative ai", "llm"]),
    ("internet-culture", "Internet Culture & Viral Memes", "Internet culture", ["meme", "viral", "internet culture", "brainrot", "reaction image", "viral video"]),
    ("animals", "Animal & Character Memes", "Animals", ["cat", "dog", "frog", "capybara", "penguin", "animal meme", "mascot"]),
    ("gaming", "Gaming & Digital Worlds", "Gaming", ["gaming", "video game", "minecraft", "fortnite", "roblox", "indie game"]),
    ("politics", "Political & Geopolitical Memes", "Politics", ["election", "president", "political", "parliament", "geopolitical", "campaign"]),
    ("celebrity", "Celebrity & Pop Culture", "Pop culture", ["celebrity", "singer", "rapper", "actor", "influencer", "pop culture"]),
    ("science-tech", "Science & Emerging Technology", "Technology", ["robotics", "robot", "space", " nasa ", "quantum", "biotech", "technology"]),
    ("finance", "Finance & Economic Culture", "Finance", ["stock market", "inflation", "wall street", "economy", "trading", "finance"]),
]

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def parse_date(entry):
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(value), timezone.utc)
            except Exception:
                pass
    return NOW

def classify(text):
    low = f" {text.lower()} "
    matches = []
    for slug, title, category, terms in CLUSTERS:
        hits = sum(1 for term in terms if term in low)
        if hits:
            matches.append((hits, slug, title, category))
    if not matches:
        return ("general-trend", "Emerging Global Topics", "General")
    matches.sort(reverse=True)
    _, slug, title, category = matches[0]
    return slug, title, category


def supabase_post(table, rows, on_conflict=None):
    if not rows:
        return

    params = {"on_conflict": on_conflict} if on_conflict else {}

    response = requests.post(
        f"{REST}/{table}",
        params=params,
        headers=HEADERS,
        json=rows,
        timeout=30,
    )

    if not response.ok:
        log.error(
            "Supabase error %s: %s",
            response.status_code,
            response.text[:2000],
        )

    response.raise_for_status()


def supabase_get(table, params):
    h = dict(HEADERS)
    h["Prefer"] = "count=exact"

    response = requests.get(
        f"{REST}/{table}",
        params=params,
        headers=h,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def main():
    collected = {}
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"], request_headers={"User-Agent": "NarrativeRadar/1.0 research contact: admin"})
            if parsed.bozo and not parsed.entries:
                log.warning("Feed issue %s: %s", feed["name"], parsed.bozo_exception)
            for entry in parsed.entries[:80]:
                url = entry.get("link", "").strip()
                title = clean_text(entry.get("title", ""))
                if not url or not title:
                    continue
                summary = clean_text(entry.get("summary", ""))[:2500]
                published = parse_date(entry)
                slug, narrative, category = classify(title + " " + summary)
                item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
                collected[item_id] = {
                    "id": item_id, "title": title[:500], "url": url[:2000],
                    "source_name": feed["name"], "summary": summary,
                    "published_at": published.isoformat(), "first_seen_at": NOW.isoformat(),
                    "narrative_slug": slug, "narrative_title": narrative, "category": category,
                }
            log.info("%s: parsed %d entries", feed["name"], len(parsed.entries))
        except Exception as exc:
            log.exception("Feed failed: %s (%s)", feed["name"], exc)

    rows = list(collected.values())
    if rows:
        supabase_post("signals", rows, "id")
    log.info("Inserted/updated %d unique source items", len(rows))

    since = (NOW - timedelta(hours=24)).isoformat()
    recent = supabase_get("signals", {
        "select": "id,title,url,source_name,summary,published_at,first_seen_at,narrative_slug,narrative_title,category",
        "published_at": f"gte.{since}",
        "limit": "3000",
        "order": "published_at.desc",
    })

    groups = {}
    for item in recent:
        slug = item["narrative_slug"]
        groups.setdefault(slug, []).append(item)

    narrative_rows = []
    for slug, items in groups.items():
        sources = sorted(set(x["source_name"] for x in items))
        dates = []
        for x in items:
            try: dates.append(datetime.fromisoformat(x["published_at"].replace("Z", "+00:00")))
            except Exception: pass
        newest = max(dates) if dates else NOW
        oldest = min(dates) if dates else NOW
        age_hours = max(0.0, (NOW - newest).total_seconds() / 3600)
        # Heuristic, intentionally explainable. No claim of predictive accuracy.
        count_score = min(35, len(items) * 5)
        source_score = min(30, len(sources) * 10)
        freshness_score = max(0, 25 - int(age_hours))
        spread_score = min(10, max(0, (newest - oldest).total_seconds() / 3600))
        score = int(min(100, count_score + source_score + freshness_score + spread_score))
        saturation = "Low" if len(items) <= 3 else ("Medium" if len(items) <= 10 else "High")
        stage = "Emerging" if score >= 55 and saturation == "Low" else ("Growing" if score >= 40 else "Observing")
        narrative_rows.append({
            "slug": slug, "title": items[0]["narrative_title"], "category": items[0]["category"],
            "score": score, "mentions_24h": len(items), "sources_count": len(sources),
            "source_names": sources, "first_seen_at": oldest.isoformat(),
            "last_seen_at": newest.isoformat(), "saturation": saturation, "stage": stage,
            "sample_evidence": [{"title": x["title"], "url": x["url"], "source": x["source_name"]} for x in items[:5]],
            "updated_at": NOW.isoformat(),
        })
    if narrative_rows:
        supabase_post("narratives", narrative_rows, "slug")

    today = NOW.date().isoformat()
    report = {
        "report_date": today,
        "narratives_count": len(narrative_rows),
        "top_narratives": sorted(
            [{"slug": x["slug"], "title": x["title"], "score": x["score"], "stage": x["stage"], "mentions_24h": x["mentions_24h"]} for x in narrative_rows],
            key=lambda x: x["score"], reverse=True
        )[:10],
        "created_at": NOW.isoformat(),
    }
    supabase_post("daily_reports", [report], "report_date")
    log.info("Updated %d narrative clusters and daily report %s", len(narrative_rows), today)

if __name__ == "__main__":
    main()
