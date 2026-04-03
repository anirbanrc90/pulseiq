import sqlite3
from datetime import datetime

DB_PATH = "research_digest.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            url          TEXT    UNIQUE NOT NULL,
            source       TEXT,
            summary      TEXT,
            sector       TEXT,
            sentiment    TEXT,
            price_target TEXT,
            key_insight  TEXT,
            confidence   INTEGER,
            scraped_at   TEXT,
            stored_at    TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialised successfully.")


def save_articles_to_db(analysed_articles):
    conn       = get_connection()
    cursor     = conn.cursor()
    new_count  = 0
    skip_count = 0

    for article in analysed_articles:
        try:
            cursor.execute("""
               INSERT OR IGNORE INTO articles
                    (title, url, source, summary, sector,
                     sentiment, confidence, price_target,
                     key_insight, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.get("title"),
                article.get("url"),
                article.get("source"),
                article.get("summary"),
                article.get("sector"),
                article.get("sentiment"),
                article.get("confidence"),
                article.get("price_target"),
                article.get("key_insight"),
                article.get("scraped_at")
            ))
            if cursor.rowcount == 1:
                new_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"Error saving article: {e}")

    conn.commit()
    conn.close()
    print(f"Saved {new_count} new articles. Skipped {skip_count} duplicates.")
    return new_count


def get_articles(sector=None, sentiment=None, limit=50, days=None):
    conn   = get_connection()
    cursor = conn.cursor()

    query  = "SELECT * FROM articles WHERE 1=1"
    params = []

    if days:
        query += (
            " AND stored_at >= datetime('now', '-"
            + str(days) + " days')"
        )

    if sector:
        query += " AND sector = ?"
        params.append(sector)

    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)

    query += " ORDER BY stored_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM articles")
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT sentiment, COUNT(*) as count
        FROM articles
        GROUP BY sentiment
    """)
    sentiment_counts = {
        row["sentiment"]: row["count"]
        for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT sector, COUNT(*) as count
        FROM articles
        GROUP BY sector
        ORDER BY count DESC
    """)
    sector_counts = {
        row["sector"]: row["count"]
        for row in cursor.fetchall()
    }

    conn.close()
    return {
        "total":        total,
        "by_sentiment": sentiment_counts,
        "by_sector":    sector_counts
    }


if __name__ == "__main__":
    import json

    initialise_database()

    with open("analysed_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Loading {len(articles)} articles...")
    save_articles_to_db(articles)

    stats = get_stats()
    print(f"Total articles : {stats['total']}")
    print(f"By sentiment   : {stats['by_sentiment']}")
    print(f"By sector      : {stats['by_sector']}")