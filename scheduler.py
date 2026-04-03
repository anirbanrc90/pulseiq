# ─── IMPORTS ────────────────────────────────────────────────────────────────────
import schedule
import time
import smtplib
import os
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv
from gtts import gTTS

from main      import scrape_all_sources, save_articles
from analyser  import analyse_all_articles
from database  import initialise_database, save_articles_to_db, get_articles, get_stats

load_dotenv()

# ─── GMAIL CONFIG ────────────────────────────────────────────────────────────────
GMAIL_SENDER   = os.getenv("GMAIL_SENDER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# BETA DISTRIBUTION LIST
BETA_TESTERS = [
    os.getenv("GMAIL_RECEIVER"), 
    "ritabritachattakhandi@gmail.com",
    "chattas.ac@gmail.com",
    "ankansarkar@gmail.com",
    "rchattakhandi@gmail.com"
]

# ─── BUILD AUDIO FILE ────────────────────────────────────────────────────────────
def generate_audio_attachment(articles):
    """
    Creates an MP3 audio briefing from the top 5 articles.
    Returns the raw bytes of the MP3 file.
    """
    print("      Generating MP3 Audio Briefing...")
    
    # Create a broadcast-style script
    script = "Welcome to your Pulse I Q Morning Briefing. Here are the top market drivers for today. "
    
    # Limit to top 5 so the audio isn't overly long
    for i, article in enumerate(articles[:5]):
        sentiment = article.get("sentiment", "Neutral")
        title = article.get("title", "")
        insight = article.get("key_insight", "")
        
        script += f"Item {i+1}. The sentiment is {sentiment}. {title}. Key insight: {insight} "
        
    script += "That concludes your morning briefing. Have a productive trading day."

    # Generate the audio
    tts = gTTS(text=script, lang='en') 
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    
    return fp.read()

# ─── BUILD HTML EMAIL ────────────────────────────────────────────────────────────
def build_email_html(articles, stats):
    """
    Builds a clean HTML email with the morning digest.
    Matches the "Editorial Cream" PulseIQ Dashboard UI exactly.
    """

    today = datetime.now().strftime("%d %B %Y")
    
    # Dashboard Theme Colors
    bg_cream    = "#fdfbf7"
    text_main   = "#1a1a1a"
    text_muted  = "#3e3832"
    oxford_blue = "#002147"
    border_dark = "#000000"
    gold_accent = "#b8860b"

    # KPI Row construction
    sentiment_summary = ""
    for s, c in stats["by_sentiment"].items():
        colour = "#2e8b57" if s == "Bullish" else \
                 "#b22222" if s == "Bearish" else "#7a756d"
        sentiment_summary += (
            f'<div style="margin-top:8px; font-size:13px; color:{text_main};">'
            f'<strong style="color:{colour}; text-transform:uppercase; font-size:11px; letter-spacing:0.05em;">{s}:</strong> {c} articles'
            f'</div>'
        )

    # Article Cards Construction
    cards_html = ""
    for article in articles[:10]:
        sentiment  = article.get("sentiment", "Neutral")
        
        # Determine Border Colors based on dashboard logic
        if sentiment == "Bullish":
            accent_col = "#2e8b57"
        elif sentiment == "Bearish":
            accent_col = "#b22222"
        else:
            accent_col = "#7a756d"

        price_block = ""
        if article.get("price_target"):
            price_block = (
                '<div style="display:inline-block; font-size:11px; color:#000000; border:1px solid #000000; padding:4px 10px; margin-top:14px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">'
                'Target: ' + str(article["price_target"]) + '</div>'
            )

        cards_html += (
            f'<div style="background:#ffffff; border:1px solid {border_dark}; border-left:4px solid {accent_col}; padding:20px 24px; margin-bottom:16px;">'

            # Badges
            f'<div style="margin-bottom:12px;">'
            f'<span style="font-size:10px; font-weight:600; padding:4px 8px; text-transform:uppercase; letter-spacing:0.05em; border:1px solid {accent_col}; color:{accent_col}; margin-right:8px;">{sentiment}</span>'
            f'<span style="font-size:10px; font-weight:600; padding:4px 8px; text-transform:uppercase; letter-spacing:0.05em; border:1px solid {oxford_blue}; color:{oxford_blue};">{article.get("sector","Other")}</span>'
            f'</div>'

            # Title & Summary
            f'<p style="margin:0 0 10px 0; font-family:Georgia, serif; font-size:18px; font-weight:bold; color:{border_dark}; line-height:1.4;">'
            f'<a href="{article.get("url","#")}" style="color:{border_dark}; text-decoration:none;">{article.get("title","")}</a></p>'
            f'<p style="font-size:14px; color:{text_muted}; line-height:1.6; margin:0 0 16px 0;">{article.get("summary","")}</p>'

            # Insight Box
            f'<div style="background:{bg_cream}; border:1px solid #d4d0c5; padding:12px 16px; font-size:13px; color:{text_main}; line-height:1.5; font-style:italic;">'
            f'<strong style="font-family:Georgia, serif; font-style:normal; color:{oxford_blue};">Analytical Insight: </strong>{article.get("key_insight","")}'
            f'</div>'

            + price_block +
            f'</div>'
        )

    # Master Email Layout
    html = (
        f'<div style="font-family:Arial, sans-serif; background-color:{bg_cream}; padding:30px 15px;">'
        f'<div style="max-width:650px; margin:0 auto;">'

        # Header
        f'<div style="background:#ffffff; border:1px solid {border_dark}; border-top:5px solid {oxford_blue}; padding:20px 24px; margin-bottom:24px;">'
        f'<div style="font-family:Georgia, serif; font-size:24px; font-weight:bold; color:{border_dark};">🏛 PulseIQ</div>'
        f'<div style="font-size:12px; color:{text_muted}; margin-top:4px;">Morning Market Digest &nbsp;|&nbsp; Powered by Claude AI</div>'
        f'<div style="margin-top:16px; padding-top:12px; border-top:1px solid #e5e5e5; font-size:11px; color:#7a756d; font-family:monospace;">EDITION: {today}</div>'
        f'</div>'

        # Intro Banner
        f'<div style="background:#ffffff; border:1px solid {border_dark}; border-left:4px solid {gold_accent}; padding:20px 24px; margin-bottom:24px;">'
        f'<p style="font-family:Georgia, serif; font-size:16px; font-weight:bold; color:{border_dark}; margin:0 0 6px 0;">Synthesizing market noise into strategic foresight.</p>'
        f'<p style="font-size:13px; color:{text_muted}; line-height:1.6; margin:0;">Your custom institutional intelligence briefing for today\'s market open. We analysed <strong>{stats["total"]}</strong> articles overnight.</p>'
        f'<p style="font-size:13px; color:{oxford_blue}; font-weight:bold; margin-top:12px;">🎧 Audio Briefing attached below.</p>'
        + sentiment_summary +
        f'</div>'

        # Articles
        + cards_html +

        # Footer
        f'<div style="text-align:center; font-size:11px; color:#7a756d; margin-top:30px; font-family:Georgia, serif; font-style:italic;">'
        f'PulseIQ Editorial Digest<br>Data provided by Moneycontrol & ET Markets. AI Analysis by Anthropic Claude.'
        f'</div>'

        f'</div></div>'
    )

    return html


# ─── SEND EMAIL ──────────────────────────────────────────────────────────────────
def send_digest_email(articles, stats):
    """
    Sends the HTML digest via Gmail SMTP with an MP3 Audio Attachment.
    """

    if not all([GMAIL_SENDER, GMAIL_PASSWORD]):
        print("Gmail credentials not set in .env — skipping email.")
        return

    today   = datetime.now().strftime("%d %B %Y")
    subject = f"PulseIQ Intelligence | {today} | {stats['total']} Assets Analysed"
    
    # 1. Generate HTML Body
    html_body = build_email_html(articles, stats)
    
    # 2. Generate Audio Payload
    try:
        audio_bytes = generate_audio_attachment(articles)
    except Exception as e:
        print(f"      Audio generation failed: {e}")
        audio_bytes = None

    try:
        # Open a single secure connection to Gmail
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            
            # Loop through the distribution list
            for recipient in BETA_TESTERS:
                if not recipient or "@" not in recipient:
                    continue
                    
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"]    = f"PulseIQ Terminal <{GMAIL_SENDER}>"
                msg["To"]      = recipient
                
                # Attach HTML
                msg.attach(MIMEText(html_body, "html"))

                # 3. Attach Audio if it generated successfully
                if audio_bytes:
                    part = MIMEBase("audio", "mp3")
                    part.set_payload(audio_bytes)
                    encoders.encode_base64(part)
                    safe_date = today.replace(" ", "_")
                    part.add_header(
                        "Content-Disposition", 
                        f"attachment; filename=PulseIQ_Briefing_{safe_date}.mp3"
                    )
                    msg.attach(part)

                # Send the email
                server.sendmail(GMAIL_SENDER, recipient, msg.as_string())
                print(f"Digest email successfully sent to: {recipient}")
                
    except Exception as e:
        print(f"Email batch failed: {e}")


# ─── FULL PIPELINE ───────────────────────────────────────────────────────────────
def run_daily_pipeline():
    """
    The complete daily pipeline.
    """

    print(f"\n{'='*50}")
    print(f"Pipeline started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    print("\n[1/4] Scraping articles from Moneycontrol & ET Markets...")
    articles = scrape_all_sources()
    save_articles(articles)
    print(f"      Fetched {len(articles)} articles")

    print("\n[2/4] Analysing with Claude...")
    analysed = analyse_all_articles()
    print(f"      Analysed {len(analysed)} articles")

    print("\n[3/4] Saving to database...")
    initialise_database()
    new_count = save_articles_to_db(analysed)
    print(f"      Saved {new_count} new articles")

    print("\n[4/4] Sending Gmail digest batch with Audio...")
    stats    = get_stats()
    articles = get_articles(limit=10) 
    send_digest_email(articles, stats)

    print(f"\nPipeline complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")


# ─── SCHEDULER ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("🏛 PulseIQ — Scheduler starting...")
    print("Pipeline scheduled for exactly 09:00 AM daily (Pre-market execution).")
    print("Running initial synchronization now...\n")

    run_daily_pipeline()

    schedule.every().day.at("09:00").do(run_daily_pipeline)

    print("\nScheduler running. PulseIQ is active. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)