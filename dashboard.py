import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io
from dotenv import load_dotenv
import anthropic
from database import get_articles, get_stats, initialise_database
import streamlit_authenticator as stauth
from gtts import gTTS

load_dotenv()

# Reads from .env locally, from st.secrets on Streamlit Cloud
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

st.set_page_config(
    page_title="PulseIQ — Institutional Intelligence",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── AUTHENTICATION CREDENTIALS ───────────────────────────────────────────────
credentials = {
    "usernames": {
        "anirban": {
            "name":     "Anirban Roychowdhury",
            "password": "$2b$12$ikGRqx6UJ2715IsO4oSR4.jgzDTk6sT7GX5GswTwEKS6hnDqgnKsK"
        },
        "demo": {
            "name":     "Demo User",
            "password": "$2b$12$x.utI2MpFv6DxJhMy2mFI.5uHO5GsdtHfChJgdpYVh5jaz1UTsHne"
        }
    }
}

cookie_config = {
    "name":        "pulseiq_auth",
    "key":         "pulseiq_institutional_secret_key_secure_2026",
    "expiry_days": 1
}

# ── THEME STYLING (MUST BE LOADED FIRST) ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Lora:ital,wght@0,400;0,600;0,700;1,400&display=swap');

/* Base Theme - Editorial Cream */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: #fdfbf7 !important; 
    color: #1a1a1a !important; 
}

/* Force Serif for Headings */
h1, h2, h3, .editorial-heading {
    font-family: 'Lora', serif !important;
    color: #000000 !important;
}

.block-container {
    padding: 1.5rem 2.5rem 3rem 2.5rem !important;
    max-width: 1400px;
}

/* Override Streamlit UI Elements */
div[data-testid="stVerticalBlockBorderWrapper"] > div, 
[data-testid="stForm"] {
    border-radius: 0px !important;
    border: 1px solid #000000 !important;
    background: #ffffff !important;
    box-shadow: 4px 4px 0px rgba(0,0,0,0.03) !important;
}

/* Fix Input Boxes to be Bold and Completely Connected */
div[data-baseweb="input"], 
div[data-baseweb="select"] > div, 
.stButton > button,
div[data-testid="stDownloadButton"] > button {
    border-radius: 0px !important;
    border: 2px solid #000000 !important; 
    box-shadow: none !important;
    background-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s;
}

/* Focus State for Inputs */
div[data-baseweb="input"]:focus-within, 
div[data-baseweb="select"] > div:focus-within {
    border-color: #002147 !important; 
}

/* Strip native inner borders to prevent clashing/clipping */
div[data-baseweb="input"] > div,
input[type="text"], 
input[type="password"] {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
}

.stButton > button, div[data-testid="stDownloadButton"] > button {
    background-color: #fdfbf7 !important;
    color: #000000 !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    transition: all 0.2s;
    width: 100%;
}
.stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover {
    background-color: #002147 !important; 
    color: #ffffff !important;
}

/* ── HEADER & INTRO ── */
.piq-header {
    background: #ffffff;
    border: 1px solid #000000;
    border-top: 5px solid #002147; 
    padding: 20px 28px;
    margin-bottom: 16px; 
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.piq-name { font-family: 'Lora', serif; font-size: 26px; font-weight: 700; color: #000000; letter-spacing: -0.5px; }
.piq-tagline { font-size: 13px; color: #3e3832; margin-top: 4px; }
.piq-live { border: 1px solid #2e8b57; color: #2e8b57; font-size: 11px; font-weight: 600; padding: 4px 14px; letter-spacing: 0.05em; text-transform: uppercase; }
.piq-time { font-size: 11px; color: #7a756d; font-family: monospace; margin-top: 6px; text-align: right; }

.piq-intro-banner {
    background: #ffffff;
    border: 1px solid #000000;
    border-left: 4px solid #b8860b; 
    padding: 20px 28px;
    margin-bottom: 24px;
}
.piq-intro-lead {
    font-family: 'Lora', serif;
    font-size: 16px;
    font-weight: 700;
    color: #000000;
    margin-bottom: 6px;
}
.piq-intro-text {
    font-size: 14px;
    color: #3e3832;
    line-height: 1.6;
}

/* ── KPI CARDS ── */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: #ffffff; border: 1px solid #000000; padding: 20px 24px; }
.kpi-accent-blue { border-top: 4px solid #002147; } 
.kpi-accent-green { border-top: 4px solid #2e8b57; } 
.kpi-accent-red { border-top: 4px solid #b22222; } 
.kpi-accent-violet { border-top: 4px solid #b8860b; } 
.kpi-label { font-size: 11px; font-weight: 600; color: #3e3832; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.kpi-value { font-family: 'Lora', serif; font-size: 34px; font-weight: 700; color: #000000; line-height: 1; margin-bottom: 8px; }
.kpi-delta { font-size: 12px; color: #3e3832; font-weight: 500; }
.kpi-delta-up { color: #2e8b57; }
.kpi-delta-down { color: #b22222; }

/* ── EXECUTIVE BRIEFING ── */
.exec-card { background: #ffffff; border: 1px solid #000000; border-left: 5px solid #002147; padding: 24px 30px; margin-bottom: 12px;}
.exec-eyebrow { font-size: 11px; font-weight: 600; color: #002147; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.exec-heading { font-family: 'Lora', serif; font-size: 18px; font-weight: 700; color: #000000; margin-bottom: 18px; }
.exec-bullet { display: flex; gap: 12px; margin-bottom: 14px; align-items: flex-start; }
.exec-dot { width: 6px; height: 6px; background: #000000; margin-top: 8px; flex-shrink: 0; }
.exec-text { font-size: 14px; color: #1a1a1a; line-height: 1.6; }
.exec-text strong { color: #000000; }

/* ── CHATBOT TERMINAL ── */
.chat-container-card { background: #ffffff; border: 1px solid #000000; padding: 24px 30px; height: 100%; display: flex; flex-direction: column; }
.chat-messages { display: flex; flex-direction: column; gap: 12px; padding: 10px 0 10px 0; }
.chat-msg-user { align-self: flex-end; background: #002147; color: #ffffff; padding: 12px 16px; font-size: 13px; max-width: 90%; line-height: 1.5; border: 1px solid #000000; }
.chat-msg-bot { align-self: flex-start; background: #fdfbf7; color: #1a1a1a; padding: 12px 16px; font-size: 13px; max-width: 95%; line-height: 1.6; border: 1px solid #000000; }
.chat-msg-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.chat-empty { text-align: center; color: #3e3832; font-size: 13px; padding: 60px 20px; line-height: 1.6; border: 1px dashed #d4d0c5; }

/* ── ARTICLE CARDS ── */
.art-card { background: #ffffff; border: 1px solid #000000; padding: 22px 26px; margin-bottom: 16px; transition: transform 0.2s ease; }
.art-card:hover { transform: translateY(-2px); box-shadow: 4px 4px 0px rgba(0,0,0,0.05); }
.art-card-bull { border-left: 4px solid #2e8b57; }
.art-card-bear { border-left: 4px solid #b22222; }
.art-card-neut { border-left: 4px solid #7a756d; }
.badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.badge { font-size: 10px; font-weight: 600; padding: 4px 8px; text-transform: uppercase; letter-spacing: 0.05em; border: 1px solid #000000; }
.badge-bull { background: transparent; color: #2e8b57; border-color: #2e8b57; }
.badge-bear { background: transparent; color: #b22222; border-color: #b22222; }
.badge-neut { background: transparent; color: #3e3832; border-color: #3e3832; }
.badge-sect { background: transparent; color: #002147; border-color: #002147; }
.badge-src  { background: transparent; color: #1a1a1a; border-color: #1a1a1a; }
.badge-watch{ background: #b8860b; color: #ffffff; border-color: #b8860b; }
.art-title { font-family: 'Lora', serif; font-size: 18px; font-weight: 700; color: #000000; margin: 0 0 10px 0; line-height: 1.4; }
.art-title a { color: #000000; text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s; }
.art-title a:hover { border-bottom: 1px solid #000000; }
.art-summary { font-size: 15px; color: #3e3832; line-height: 1.6; margin-bottom: 16px; }
.art-insight { background: #fdfbf7; border: 1px solid #d4d0c5; padding: 12px 16px; font-size: 14px; color: #1a1a1a; line-height: 1.5; font-style: italic; }
.art-insight strong { font-family: 'Lora', serif; font-style: normal; color: #002147; }
.art-price { display: inline-block; font-size: 12px; color: #000000; border: 1px solid #000000; padding: 4px 10px; margin-top: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.art-meta { font-size: 12px; color: #7a756d; margin-top: 16px; font-family: monospace; }

/* ── SIDEBAR & MISC ── */
section[data-testid="stSidebar"] { background: #fdfbf7 !important; border-right: 1px solid #000000 !important; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label { color: #1a1a1a !important; }
section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] .stSlider label { font-weight: 600 !important; font-size: 11px !important; color: #000000 !important; text-transform: uppercase; letter-spacing: 0.05em; }
hr { border-color: #d4d0c5 !important; margin: 2rem 0 !important; border-style: solid; }
.piq-footer { text-align: center; font-size: 12px; color: #7a756d; padding: 24px 0 12px; font-family: 'Lora', serif; font-style: italic; }
.art-count { font-size: 14px; color: #3e3832; margin: 8px 0 20px; font-family: 'Lora', serif; }

/* Remove padding from chat input form */
[data-testid="stForm"] { padding: 0 !important; margin: 0 !important; border: none !important; box-shadow: none !important; background: transparent !important; }

/* HIDE STREAMLIT 'PRESS ENTER TO SUBMIT' TEXT */
div[data-testid="InputInstructions"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── AUTHENTICATION ENGINE ────────────────────────────────────────────────────
authenticator = stauth.Authenticate(
    credentials,
    cookie_config["name"],
    cookie_config["key"],
    cookie_config["expiry_days"]
)

if not st.session_state.get("authentication_status"):
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    with col2:
        st.markdown("""
        <div style="text-align:center; padding-top: 80px; padding-bottom: 10px;">
          <div style="font-family:'Lora', serif; font-size:48px; font-weight:700; color:#000000; line-height: 1;">🏛 PulseIQ</div>
          <div style="font-family:'Inter', sans-serif; font-size:12px; font-weight:600; color:#3e3832; margin-top:12px; text-transform:uppercase; letter-spacing:0.15em;">
            Institutional Market Intelligence
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        name, authentication_status, username = authenticator.login(
            fields={
                "Form name": "",
                "Username":  "Terminal ID",
                "Password":  "Access Code",
                "Login":     "Authenticate"
            },
            location="main"
        )
        
        if authentication_status is False:
            st.error("Authentication failed. Invalid Terminal ID or Access Code.")
            
        elif authentication_status is None:
            st.markdown("""
            <div style="text-align:center; margin-top: 30px; font-size:12px; color:#7a756d; font-family:'Lora', serif; font-style:italic;">
                Authorized Personnel Only. <br>Powered by Claude AI
            </div>
            """, unsafe_allow_html=True)
            
    st.stop()

# ── MAIN DASHBOARD (RUNS ONLY IF AUTHENTICATED) ──────────────────────────────
name = st.session_state["name"]
authenticator.logout("Sign out", location="sidebar")
st.sidebar.markdown(
    f'<p style="font-size:12px;color:#3e3832;margin:-8px 0 16px 0; font-family:\'Inter\', sans-serif;">'
    f'Signed in as <strong style="color:#000000">{name}</strong></p>',
    unsafe_allow_html=True
)

# ── INIT ─────────────────────────────────────────────────────────────────────
initialise_database()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── HELPERS ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def generate_executive_briefing(cache_key, portfolio_context=""):
    articles = get_articles(limit=15)
    if not articles:
        return []
    headlines = "\n".join(
        f"- [{a['sentiment']}][{a['sector']}] {a['title']}"
        for a in articles
    )
    
    if portfolio_context:
        prompt = (
            "You are a Chief Investment Strategist presenting a morning briefing to an institutional client.\n\n"
            f"CRITICAL: The client's active portfolio is: {portfolio_context}\n\n"
            "Based on today's market headlines, write exactly 5 bullet points summarising key market themes, risks, and opportunities.\n"
            "You MUST evaluate how the news impacts their specific holdings. If a headline affects their portfolio, calculate an [Impact Score: 1-10] and append it to the end of the bullet point.\n"
            "Each bullet must start with a bold theme label like **Macro:**, **Risk:**, **Opportunity:**, **[Ticker]:**\n"
            "Be sharp, specific, and actionable. Max 35 words per bullet.\n\n"
            "Headlines:\n" + headlines + "\n\n"
            "Return only the 5 bullet points. No preamble. No numbering."
        )
    else:
        prompt = (
            "You are a Chief Investment Strategist presenting a morning briefing to HNI wealth management clients.\n\n"
            "Based on today's market headlines, write exactly 5 bullet points summarising key market themes, risks, and opportunities.\n"
            "Each bullet must start with a bold theme label like **Macro:**, **Risk:**, **Opportunity:**, **BFSI:**, **Growth:**\n"
            "Be sharp, specific, and actionable. Max 25 words per bullet.\n\n"
            "Headlines:\n" + headlines + "\n\n"
            "Return only the 5 bullet points. No preamble. No numbering."
        )

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        return [
            l.strip().lstrip("-•* ")
            for l in raw.split("\n")
            if l.strip()
        ]
    except Exception as e:
        return [f"Briefing unavailable: {e}"]

# 🔴 FEATURE: GENERATIVE AUDIO CACHING
@st.cache_data(ttl=3600)
def generate_audio_bytes(bullets_text):
    text_to_read = "Here is your Pulse I Q Executive Briefing. " + bullets_text
    # Removed tld='co.in' to prevent 403 Forbidden routing blocks on corporate networks
    tts = gTTS(text=text_to_read, lang='en') 
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()

def build_csv(articles):
    df   = pd.DataFrame(articles)
    cols = ["title","source","sector","sentiment",
            "summary","key_insight","price_target","url","scraped_at"]
    df   = df[[c for c in cols if c in df.columns]]
    return df.to_csv(index=False).encode("utf-8")

def render_bullet(text):
    parts = text.split(":", 1)
    if len(parts) == 2:
        label = parts[0].replace("**","").strip()
        body  = parts[1].strip()
        return (
            '<div class="exec-bullet">'
            '<div class="exec-dot"></div>'
            '<div class="exec-text">'
            '<strong>' + label + ':</strong> ' + body +
            '</div></div>'
        )
    return (
        '<div class="exec-bullet">'
        '<div class="exec-dot"></div>'
        '<div class="exec-text">' + text.replace("**","") + '</div>'
        '</div>'
    )

# ── DATA ─────────────────────────────────────────────────────────────────────
stats    = get_stats()
total    = stats["total"]
bullish  = stats["by_sentiment"].get("Bullish", 0)
bearish  = stats["by_sentiment"].get("Bearish", 0)
neutral  = stats["by_sentiment"].get("Neutral",  0)
top_sect = (max(stats["by_sector"], key=stats["by_sector"].get)
            if stats["by_sector"] else "N/A")
bull_pct = round(bullish / max(total, 1) * 100)
bear_pct = round(bearish / max(total, 1) * 100)
now_str  = datetime.now().strftime("%d %b %Y  ·  %H:%M IST")

# ── SIDEBAR & WATCHLIST LOGIC ────────────────────────────────────────────────
st.sidebar.markdown(
    '<p style="font-family:\'Lora\', serif; font-size:24px;font-weight:700;color:#000000;margin:0 0 4px 0">'
    '🏛 PulseIQ</p>'
    '<p style="font-size:13px;color:#3e3832;margin:0 0 24px 0">'
    'Terminal Controls</p>',
    unsafe_allow_html=True
)

sectors    = ["All","BFSI","Energy","IT","Auto",
              "Pharma","Macro","Commodities","Other"]
sentiments = ["All","Bullish","Bearish","Neutral"]
sel_sector    = st.sidebar.selectbox("Sector",    sectors)
sel_sentiment = st.sidebar.selectbox("Sentiment", sentiments)
limit         = st.sidebar.slider("Max articles", 5, 50, 20)
st.sidebar.divider()

st.sidebar.markdown(
    '<p style="font-size:11px;font-weight:600;color:#000000;'
    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">'
    'Date Range</p>',
    unsafe_allow_html=True
)
date_range = st.sidebar.radio(
    "date_range",
    ["Today", "Last 3 days", "Last 7 days", "All time"],
    label_visibility="collapsed"
)
days_map = {
    "Today":       1,
    "Last 3 days": 3,
    "Last 7 days": 7,
    "All time":    None
}

st.sidebar.divider()
st.sidebar.markdown(
    '<p style="font-size:11px;font-weight:600;color:#000000;'
    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">'
    'Portfolio Weights</p>',
    unsafe_allow_html=True
)
watchlist_raw = st.sidebar.text_input(
    "Portfolio Weights",
    placeholder="e.g. HDFC:40, Reliance:30, INFY:30",
    label_visibility="collapsed",
    help="Enter ticker symbols and optional weights to customize the AI Executive Briefing."
)

portfolio_dict = {}
watchlist_tickers = []
if watchlist_raw:
    for item in watchlist_raw.split(","):
        parts = item.split(":")
        ticker = parts[0].strip().upper()
        weight = parts[1].strip() + "%" if len(parts) > 1 else "Unspecified Weight"
        if ticker:
            portfolio_dict[ticker] = weight
            watchlist_tickers.append(ticker)

portfolio_context_str = ", ".join([f"{k} ({v})" for k, v in portfolio_dict.items()])

st.sidebar.divider()
st.sidebar.markdown(
    '<p style="font-size:11px;font-weight:600;color:#000000;'
    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">'
    "Today's Metrics</p>",
    unsafe_allow_html=True
)
icons = {"Bullish":"↑","Bearish":"↓","Neutral":"—"}
for s, c in stats["by_sentiment"].items():
    st.sidebar.markdown(
        f'<p style="font-size:14px;color:#1a1a1a;margin:6px 0">'
        f'<span style="font-weight:bold; font-family:monospace">{icons.get(s,"•")}</span> <strong style="color:#000000">{s}:</strong> '
        f'{c}</p>',
        unsafe_allow_html=True
    )

st.sidebar.divider()
st.sidebar.markdown(
    '<p style="font-size:11px;font-weight:600;color:#000000;'
    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">'
    'Sector Breakdown</p>',
    unsafe_allow_html=True
)
for s, c in stats["by_sector"].items():
    st.sidebar.markdown(
        f'<p style="font-size:14px;color:#1a1a1a;margin:4px 0">'
        f'<strong style="color:#000000">{s}:</strong> {c}</p>',
        unsafe_allow_html=True
    )

# ── HEADER & INTRO DESCRIPTION ────────────────────────────────────────────────
st.markdown(f"""
<div class="piq-header">
  <div>
    <div class="piq-name">🏛 PulseIQ</div>
    <div class="piq-tagline">
       Morning Market Digest &nbsp;|&nbsp; Powered by Claude AI
    </div>
  </div>
  <div style="text-align:right">
    <div class="piq-live">LIVE EDITION</div>
    <div class="piq-time">{now_str}</div>
  </div>
</div>

<div class="piq-intro-banner">
  <div class="piq-intro-lead">Synthesizing market noise into strategic foresight.</div>
  <div class="piq-intro-text">
    PulseIQ deploys advanced AI to parse high-volume financial data, quantifying sentiment and isolating sector-specific momentum. Engineered for data-driven investors and financial professionals, our platform delivers an unfiltered, real-time edge for rigorous risk assessment and precise market execution.
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI CARDS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card kpi-accent-blue">
    <div class="kpi-label">Volume Analysed</div>
    <div class="kpi-value">{total}</div>
    <div class="kpi-delta">Today's coverage</div>
  </div>
  <div class="kpi-card kpi-accent-green">
    <div class="kpi-label">Bullish Sentiments</div>
    <div class="kpi-value" style="color:#2e8b57">{bullish}</div>
    <div class="kpi-delta kpi-delta-up">↑ {bull_pct}% of today's articles</div>
  </div>
  <div class="kpi-card kpi-accent-red">
    <div class="kpi-label">Bearish Sentiments</div>
    <div class="kpi-value" style="color:#b22222">{bearish}</div>
    <div class="kpi-delta kpi-delta-down">↓ {bear_pct}% of today's articles</div>
  </div>
  <div class="kpi-card kpi-accent-violet">
    <div class="kpi-label">Primary Sector</div>
    <div class="kpi-value" style="font-size:24px;padding-top:8px">{top_sect}</div>
    <div class="kpi-delta">{stats["by_sector"].get(top_sect,0)} articles today</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SPRINT 3: SENTIMENT VOLATILITY RADAR ─────────────────────────────────────
with st.container(border=True):
    st.markdown('<div class="exec-eyebrow">Analytics Moat</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-heading" style="margin-bottom: 8px;">Sentiment Volatility Radar (14-Day Trend)</div>', unsafe_allow_html=True)
    
    trend_arts = get_articles(limit=500, days=14)
    if trend_arts:
        df_trend = pd.DataFrame(trend_arts)
        if "scraped_at" in df_trend.columns and "sentiment" in df_trend.columns:
            df_trend["Date"] = pd.to_datetime(df_trend["scraped_at"], errors="coerce").dt.date
            df_trend = df_trend.dropna(subset=["Date"])
            
            trend_grouped = df_trend.groupby(["Date", "sentiment"]).size().reset_index(name="Volume")
            
            fig_trend = px.line(
                trend_grouped, x="Date", y="Volume", color="sentiment",
                color_discrete_map={"Bullish":"#2e8b57", "Bearish":"#b22222", "Neutral":"#7a756d"},
                markers=True
            )
            
            fig_trend.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#3e3832", family="Inter", size=12),
                xaxis=dict(title="", showgrid=False, linecolor="#000000", tickfont=dict(color="#1a1a1a")),
                yaxis=dict(title="Article Volume", gridcolor="#e5e5e5", linecolor="#000000", tickfont=dict(color="#1a1a1a")),
                margin=dict(l=10, r=10, t=10, b=10),
                height=250,
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, title="")
            )
            fig_trend.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color="#000000")))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Insufficient data properties for trend analysis.")
    else:
        st.info("Insufficient historical data for trend analysis.")

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ── SIDE-BY-SIDE: BRIEFING & CHATBOT ──────────────────────────────────────────
col_briefing, col_chat = st.columns([1.6, 1])

with col_briefing:
    cache_key = str(sorted([a["title"] for a in get_articles(limit=15)])) + portfolio_context_str
    with st.spinner("Compiling the executive briefing..."):
        bullets = generate_executive_briefing(cache_key, portfolio_context_str)

    bullets_html = "".join(render_bullet(b) for b in bullets)
    
    portfolio_badge = ""
    if portfolio_context_str:
        portfolio_badge = '<span style="float:right; font-size:10px; background:#b8860b; color:#fff; padding:3px 8px; font-family:\'Inter\', sans-serif; letter-spacing:0.05em; text-transform:uppercase;">Portfolio Synced</span>'
        
    st.markdown(f"""
    <div class="exec-card">
      <div class="exec-eyebrow">Strategic Overview {portfolio_badge}</div>
      <div class="exec-heading">The Executive Briefing</div>
      {bullets_html}
    </div>
    """, unsafe_allow_html=True)
    
  # 🔴 FEATURE: GENERATIVE AUDIO PLAYER
    # We clean the markdown bold asterisks out before generating the audio
    clean_bullets_text = " ".join([b.replace("**", "") for b in bullets])
    try:
        audio_bytes = generate_audio_bytes(clean_bullets_text)
        st.audio(audio_bytes, format="audio/mp3")
    except Exception as e:
        # Fails gracefully without breaking the UI for the user
        st.warning("🎧 Audio briefing temporarily unavailable due to network restrictions.")

with col_chat:
    st.markdown("""
    <div class="chat-container-card">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #002147; padding-bottom: 8px; margin-bottom: 12px;">
          <div>
              <div class="exec-eyebrow" style="margin-bottom:0;">Interactive</div>
              <div class="exec-heading" style="margin:0; font-size:16px;">✦ Analyst Terminal</div>
          </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    red_team_mode = st.toggle("🔴 Enable Red Team Mode", help="Forces the AI to take a bearish, devil's advocate stance.")
    
    with st.container(height=260, border=False):
        if not st.session_state.chat_history:
            st.markdown(
                '<div class="chat-empty">'
                'Awaiting your inquiry.<br><br>'
                '<strong style="color:#000000">Example:</strong><br>"What is the consensus on IT today?"'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            messages_html = '<div class="chat-messages">'
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    messages_html += (
                        '<div class="chat-msg-user">'
                        '<div class="chat-msg-label" style="color:rgba(255,255,255,0.7)">Inquiry</div>'
                        + msg["content"] + '</div>'
                    )
                else:
                    messages_html += (
                        '<div class="chat-msg-bot">'
                        '<div class="chat-msg-label" style="color:#002147">PulseIQ</div>'
                        + msg["content"] + '</div>'
                    )
            messages_html += '</div>'
            st.markdown(messages_html, unsafe_allow_html=True)
            
    with st.form("chat_form", clear_on_submit=True, border=False):
        input_col, btn_col, clear_col = st.columns([6, 2, 2])
        with input_col:
            user_question = st.text_input("Ask", label_visibility="collapsed", placeholder="Consult the analyst...")
        with btn_col:
            submit = st.form_submit_button("Send", use_container_width=True)
        with clear_col:
            clear = st.form_submit_button("Clear", use_container_width=True)
            
        if clear:
            st.session_state.chat_history = []
            st.rerun()

        if submit and user_question.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_question.strip()})

            context_articles = get_articles(limit=20)
            context = "\n\n".join([
                f"Title: {a.get('title','')}\n"
                f"Sector: {a.get('sector','')}\n"
                f"Sentiment: {a.get('sentiment','')}\n"
                f"Summary: {a.get('summary','')}\n"
                f"Key insight: {a.get('key_insight','')}"
                for a in context_articles
            ])

            system_behavior = "Use a professional, editorial tone. Be direct, analytical, and objective."
            if red_team_mode:
                system_behavior = (
                    "RED TEAM MODE ACTIVATED: You must act as a contrarian 'devil's advocate'. "
                    "Explicitly ignore the consensus, identify hidden systemic risks, and strongly "
                    "argue the bearish counter-narrative for the user's query."
                )

            prompt = (
                "You are PulseIQ, an AI market intelligence analyst providing insights "
                "for an elite financial publication.\n\n"
                f"{system_behavior}\n"
                "Answer the user's question using ONLY the following articles "
                "from today's market coverage.\n"
                "If the answer is not in today's articles, state: 'Insufficient data in current coverage.'\n\n"
                "TODAY'S ARTICLES:\n" + context +
                "\n\nUSER QUESTION: " + user_question +
                "\n\nAnswer in 3-4 sentences."
            )

            with st.spinner("Consulting coverage..."):
                try:
                    response = client.messages.create(
                        model      = "claude-haiku-4-5-20251001",
                        max_tokens = 400,
                        messages   = [{"role": "user", "content": prompt}]
                    )
                    answer = response.content[0].text.strip()
                except Exception as e:
                    answer = f"System error retrieving data: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()
            
    if st.session_state.chat_history:
        memo_content = "# PulseIQ Investment Memo\n"
        memo_content += f"**Date Executed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        if portfolio_context_str:
            memo_content += f"**Active Portfolio Strategy:** {portfolio_context_str}\n"
        memo_content += "---\n\n"
        for msg in st.session_state.chat_history:
            role_title = "Client Inquiry" if msg["role"] == "user" else "PulseIQ Analyst Intelligence"
            memo_content += f"### {role_title}\n{msg['content']}\n\n"
        
        st.download_button(
            label="📄 Download Investment Memo",
            data=memo_content,
            file_name=f"PulseIQ_Memo_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ── SEARCH + EXPORT ───────────────────────────────────────────────────────────
s_col, e_col = st.columns([3, 1])
with s_col:
    search_q = st.text_input(
        "Search Database", placeholder="Search parameters (e.g., 'RBI', 'Oil')",
        label_visibility="collapsed"
    )
with e_col:
   export_arts = get_articles(
        sector    = None if sel_sector    == "All" else sel_sector,
        sentiment = None if sel_sentiment == "All" else sel_sentiment,
        limit     = limit,
        days      = days_map.get(date_range)
    )
   st.download_button(
        label     = "Download Data [CSV]",
        data      = build_csv(export_arts),
        file_name = f"pulseiq_{datetime.now().strftime('%Y%m%d')}.csv",
        mime      = "text/csv",
        width     = "stretch"
    )

# ── CHARTS ───────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

CHART_LAYOUT = dict(
    plot_bgcolor  = "rgba(0,0,0,0)",
    paper_bgcolor = "rgba(0,0,0,0)",
    font          = dict(color="#3e3832", family="Inter", size=12),
    title_font    = dict(color="#000000", size=16, family="Lora", weight="bold"),
    showlegend    = False,
    height        = 280,
    margin        = dict(l=10, r=10, t=50, b=10),
    xaxis = dict(gridcolor="#e5e5e5", linecolor="#000000", tickfont=dict(color="#1a1a1a")),
    yaxis = dict(gridcolor="#e5e5e5", linecolor="#000000", tickfont=dict(color="#1a1a1a"))
)

with col_l:
    sent_df = pd.DataFrame({
        "Sentiment": list(stats["by_sentiment"].keys()),
        "Count":     list(stats["by_sentiment"].values())
    })
    fig_s = px.bar(
        sent_df, x="Sentiment", y="Count",
        color="Sentiment",
        color_discrete_map={
            "Bullish":"#2e8b57", 
            "Bearish":"#b22222", 
            "Neutral":"#7a756d"  
        },
        title="Sentiment Distribution"
    )
    fig_s.update_layout(**CHART_LAYOUT)
    fig_s.update_traces(marker_line_width=1, marker_line_color="#000000", marker_cornerradius=0)
    st.plotly_chart(fig_s, width="stretch")

with col_r:
    sect_df = pd.DataFrame({
        "Sector": list(stats["by_sector"].keys()),
        "Count":  list(stats["by_sector"].values())
    }).sort_values("Count", ascending=True)
    fig_sec = px.bar(
        sect_df, x="Count", y="Sector",
        orientation="h",
        title="Volume by Sector",
        color="Count",
        color_continuous_scale=[
            [0.0, "#d1d5db"],
            [0.5, "#4b5563"],
            [1.0, "#002147"] 
        ]
    )
    fig_sec.update_layout(**CHART_LAYOUT)
    fig_sec.update_layout(coloraxis_showscale=False)
    fig_sec.update_traces(marker_line_width=1, marker_line_color="#000000", marker_cornerradius=0)
    st.plotly_chart(fig_sec, width="stretch")

st.divider()

# ── FETCH + FILTER ────────────────────────────────────────────────────────────
articles = get_articles(
    sector    = None if sel_sector    == "All" else sel_sector,
    sentiment = None if sel_sentiment == "All" else sel_sentiment,
    limit     = limit,
    days      = days_map.get(date_range)
)
if search_q:
    q        = search_q.lower()
    articles = [
        a for a in articles
        if q in (a.get("title","")       or "").lower()
        or q in (a.get("summary","")     or "").lower()
        or q in (a.get("key_insight","") or "").lower()
        or q in (a.get("sector","")      or "").lower()
    ]

st.markdown(
    f'<p class="art-count">Displaying '
    f'<strong>{len(articles)}</strong> records</p>',
    unsafe_allow_html=True
)

if not articles:
    st.info("No records match the current parameters.")
    st.stop()

# ── ARTICLE CARDS ─────────────────────────────────────────────────────────────
for article in articles:
    sentiment  = article.get("sentiment", "Neutral")
    sector     = article.get("sector",    "Other")
    title      = article.get("title",     "Untitled")
    url        = article.get("url",       "#")
    summary    = article.get("summary",   "No summary available.")
    insight    = article.get("key_insight", "")
    price_tgt  = article.get("price_target")
    source     = article.get("source", "")
    scraped    = str(article.get("scraped_at",""))[:10]
    confidence = article.get("confidence")

    card_cls   = ("bull" if sentiment == "Bullish"
                  else "bear" if sentiment == "Bearish"
                  else "neut")
    badge_cls  = "badge-" + card_cls

    is_watch = (
        any(w in (title   or "").upper() or
            w in (summary or "").upper()
            for w in watchlist_tickers)
        if watchlist_tickers else False
    )

    watch_badge  = (
        '<span class="badge badge-watch">PORTFOLIO</span>'
        if is_watch else ""
    )
    price_block  = (
        '<div class="art-price">Target: ' + str(price_tgt) + '</div>'
        if price_tgt else ""
    )
    src_badge = (
        '<span class="badge badge-src">' + source + '</span>'
        if source else ""
    )

    if confidence:
        conf_int   = int(confidence)
        bar_color  = (
            "#2e8b57" if conf_int >= 80 
            else "#b8860b" if conf_int >= 65 
            else "#b22222" 
        )
        confidence_block = (
            '<div style="margin-top:12px;display:flex;'
            'align-items:center;gap:10px;">'
            '<span style="font-size:11px;color:#3e3832;'
            'width:120px;flex-shrink:0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">'
            'AI Confidence</span>'
            '<div style="flex:1;height:2px;background:#e5e5e5;">'
            '<div style="width:' + str(conf_int) + '%;height:2px;'
            'background:' + bar_color + ';"></div>'
            '</div>'
            '<span style="font-size:11px;font-weight:700;'
            'color:' + bar_color + ';width:36px;text-align:right;">'
            + str(conf_int) + '%</span>'
            '</div>'
        )
    else:
        confidence_block = ""

    st.markdown(
        '<div class="art-card art-card-' + card_cls + '">'
        '<div class="badge-row">'
        '<span class="badge ' + badge_cls + '">' + sentiment + '</span>'
        '<span class="badge badge-sect">' + sector + '</span>'
        + src_badge + watch_badge +
        '</div>'
        '<div class="art-title">'
        '<a href="' + url + '" target="_blank">' + title + '</a>'
        '</div>'
        '<div class="art-summary">' + summary + '</div>'
        '<div class="art-insight">'
        '<strong>Analytical Insight: </strong>' + insight +
        '</div>'
        + confidence_block +
        price_block +
        '<div class="art-meta">SOURCE: ' + source.upper() + ' &nbsp;|&nbsp; PUBLISHED: ' + scraped + '</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<div class="piq-footer">'
    'PulseIQ Editorial Digest<br>'
    'Data provided by Moneycontrol & ET Markets. AI Analysis by Anthropic Claude.<br>'
    'Developed by Anirban Roychowdhury.'
    '</div>',
    unsafe_allow_html=True
)