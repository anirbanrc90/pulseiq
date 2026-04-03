# ─── IMPORTS ────────────────────────────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# ─── HEADERS ─────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


# ─── SOURCE 1: MONEYCONTROL ───────────────────────────────────────────────────────
def scrape_moneycontrol():
    """
    Scrapes latest market news from Moneycontrol.
    Returns list of article dicts.
    """
    url = "https://www.moneycontrol.com/news/business/markets/"
    print("  Fetching from Moneycontrol...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup     = BeautifulSoup(response.text, "html.parser")
        articles = []

        for item in soup.select("li.clearfix")[:15]:
            title_tag = item.find("a")
            if title_tag and len(title_tag.text.strip()) > 20:
                articles.append({
                    "title":      title_tag.text.strip(),
                    "url":        title_tag.get("href", ""),
                    "source":     "Moneycontrol",
                    "scraped_at": datetime.now().isoformat()
                })

        print(f"  Found {len(articles)} articles from Moneycontrol")
        return articles

    except Exception as e:
        print(f"  Moneycontrol scrape failed: {e}")
        return []


# ─── SOURCE 2: ET MARKETS ────────────────────────────────────────────────────────
def scrape_et_markets():
    """
    Scrapes latest market news from Economic Times Markets.
    Returns list of article dicts.
    """
    url = "https://economictimes.indiatimes.com/markets/stocks/news"
    print("  Fetching from ET Markets...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup     = BeautifulSoup(response.text, "html.parser")
        articles = []

        # ET Markets uses article tags with specific classes
        for item in soup.select("div.eachStory")[:15]:
            title_tag = item.find("h3")
            link_tag  = item.find("a")

            if title_tag and link_tag:
                title = title_tag.text.strip()
                href  = link_tag.get("href", "")

                # Make sure URL is absolute
                if href.startswith("/"):
                    href = "https://economictimes.indiatimes.com" + href

                if len(title) > 20:
                    articles.append({
                        "title":      title,
                        "url":        href,
                        "source":     "ET Markets",
                        "scraped_at": datetime.now().isoformat()
                    })

        # Fallback selector if eachStory returns nothing
        if not articles:
            for item in soup.select("div.story-box")[:15]:
                title_tag = item.find(["h3","h4","a"])
                link_tag  = item.find("a")
                if title_tag and link_tag:
                    title = title_tag.text.strip()
                    href  = link_tag.get("href","")
                    if href.startswith("/"):
                        href = "https://economictimes.indiatimes.com" + href
                    if len(title) > 20:
                        articles.append({
                            "title":      title,
                            "url":        href,
                            "source":     "ET Markets",
                            "scraped_at": datetime.now().isoformat()
                        })

        print(f"  Found {len(articles)} articles from ET Markets")
        return articles

    except Exception as e:
        print(f"  ET Markets scrape failed: {e}")
        return []


# ─── COMBINED SCRAPER ────────────────────────────────────────────────────────────
def scrape_all_sources():
    """
    Runs all scrapers and returns a combined, deduplicated list.
    Deduplication is by title similarity to avoid near-duplicates
    before they even reach the database.
    """
    print("\n[Scraper] Starting all sources...")

    mc_articles = scrape_moneycontrol()
    et_articles = scrape_et_markets()

    combined = mc_articles + et_articles

    # Deduplicate by URL
    seen_urls  = set()
    unique     = []
    for article in combined:
        url = article.get("url","")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    print(f"\n[Scraper] Total unique articles: {len(unique)}")
    print(f"  Moneycontrol : {len(mc_articles)}")
    print(f"  ET Markets   : {len(et_articles)}")
    return unique


# ─── SAVE TO JSON ────────────────────────────────────────────────────────────────
def save_articles(articles):
    """
    Saves raw scraped articles to raw_articles.json.
    This is the staging file before Claude analyses them.
    """
    with open("raw_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"[Scraper] Saved {len(articles)} articles to raw_articles.json")


# ─── BACKWARD COMPATIBILITY ──────────────────────────────────────────────────────
def scrape_moneycontrol_only():
    """
    Kept for backward compatibility with scheduler.py.
    Use scrape_all_sources() for new code.
    """
    return scrape_moneycontrol()


# ─── MAIN ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    articles = scrape_all_sources()
    save_articles(articles)
    print("\nSample titles:")
    for a in articles[:5]:
        print(f"  [{a['source']}] {a['title'][:70]}...")