# ─── IMPORTS ────────────────────────────────────────────────────────────────────
import anthropic
import json
import os
import time
from dotenv import load_dotenv

# ─── LOAD ENVIRONMENT VARIABLES ─────────────────────────────────────────────────
load_dotenv()

# ─── INITIALISE CLAUDE CLIENT ───────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ─── ANALYSE A SINGLE ARTICLE ───────────────────────────────────────────────────
def analyse_article(article):
    """
    Sends one article title to Claude.
    Returns structured JSON with summary, sector, sentiment, and key insight.
    """

    prompt = f"""You are a senior equity research analyst at a top Indian investment bank.

Analyse this market news headline and return a JSON object with exactly these fields:

{{
 {{
  "summary": "2 sentence summary of what this means for investors",
  "sector": "one of: BFSI, Energy, IT, Auto, Pharma, Macro, Commodities, Other",
  "sentiment": "one of: Bullish, Bearish, Neutral",
  "confidence": "integer from 50 to 99 representing how confident you are in the sentiment classification",
  "price_target": "any specific price target or analyst call mentioned, or null if none",
  "key_insight": "one sharp insight a wealth manager would tell an HNI client"
}}
}}

Headline: {article['title']}
Source: {article['source']}

Return ONLY the JSON object. No explanation, no markdown, no code blocks. Start your response with {{ and end with }}."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw_response = message.content[0].text.strip()

    # ── Safety check: if response is empty, return a default ──
    if not raw_response:
        print(f"         Warning: empty response from Claude, using default")
        return build_default(article)

    # ── Find the JSON block even if Claude adds any extra text ──
    start = raw_response.find("{")
    end   = raw_response.rfind("}") + 1

    if start == -1 or end == 0:
        print(f"         Warning: no JSON found in response, using default")
        return build_default(article)

    json_str = raw_response[start:end]
    result   = json.loads(json_str)

    # ── Attach the original article metadata ──
    result["title"]      = article["title"]
    result["url"]        = article["url"]
    result["source"]     = article["source"]
    result["scraped_at"] = article["scraped_at"]

    return result


# ─── DEFAULT FALLBACK ────────────────────────────────────────────────────────────
def build_default(article):
    """
    Returns a safe default structure if Claude fails on an article.
    Enterprise code never crashes — it degrades gracefully.
    """
    return {
        "title":        article["title"],
        "url":          article["url"],
        "source":       article["source"],
        "scraped_at":   article["scraped_at"],
        "summary":      "Analysis unavailable for this article.",
        "sector":       "Other",
        "sentiment":    "Neutral",
        "price_target": None,
        "key_insight":  "Unable to generate insight for this article."
    }


# ─── ANALYSE ALL ARTICLES ────────────────────────────────────────────────────────
def analyse_all_articles():
    """
    Reads raw_articles.json, sends each article to Claude,
    saves enriched results to analysed_articles.json.
    """

    with open("raw_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Analysing {len(articles)} articles with Claude...\n")

    analysed = []

    for i, article in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] {article['title'][:60]}...")

        try:
            result = analyse_article(article)
            analysed.append(result)
            print(f"         Sector: {result['sector']} | Sentiment: {result['sentiment']}\n")

        except Exception as e:
            print(f"         Error: {e} — saving default\n")
            analysed.append(build_default(article))

        time.sleep(1.5)

    with open("analysed_articles.json", "w", encoding="utf-8") as f:
        json.dump(analysed, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Saved {len(analysed)} analysed articles to analysed_articles.json")
    return analysed


# ─── MAIN ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    analyse_all_articles()