from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import anthropic
from dotenv import load_dotenv

# Import your existing database functions
from database import get_articles, get_stats, initialise_database

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Initialize the API
app = FastAPI(title="PulseIQ Institutional API", version="1.0")

# Run database setup on startup
@app.on_event("startup")
def startup_event():
    initialise_database()

# --- DATA MODELS (Pydantic validates incoming requests) ---
class ChatRequest(BaseModel):
    user_question: str
    chat_history: List[dict] = []
    red_team_mode: bool = False

class BriefingRequest(BaseModel):
    portfolio_context: Optional[str] = None

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "PulseIQ API is live and operational."}

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Returns the high-level KPI metrics for the app home screen."""
    try:
        stats = get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/articles")
def fetch_articles(sector: str = "All", sentiment: str = "All", limit: int = 20):
    """Fetches filtered articles for the mobile feed."""
    try:
        sec = None if sector == "All" else sector
        sen = None if sentiment == "All" else sentiment
        articles = get_articles(sector=sec, sentiment=sen, limit=limit)
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/terminal/chat")
def terminal_chat(request: ChatRequest):
    """Handles the AI Analyst Terminal chat logic."""
    context_articles = get_articles(limit=15)
    context = "\n\n".join([
        f"Title: {a.get('title','')}\nSector: {a.get('sector','')}\nSentiment: {a.get('sentiment','')}\nSummary: {a.get('summary','')}"
        for a in context_articles
    ])

    system_behavior = "Use a professional, editorial tone. Be direct, analytical, and objective. Answer in 3-4 sentences."
    if request.red_team_mode:
        system_behavior = (
            "RED TEAM MODE ACTIVATED: You must act as a contrarian 'devil's advocate'. "
            "Explicitly ignore the consensus, identify hidden systemic risks, and strongly "
            "argue the bearish counter-narrative for the user's query. Answer in 3-4 sentences."
        )

    prompt = (
        "You are PulseIQ, an AI market intelligence analyst.\n\n"
        f"{system_behavior}\n"
        "Answer using ONLY the following articles. If the answer is not in the articles, state: 'Insufficient data.'\n\n"
        "TODAY'S ARTICLES:\n" + context +
        "\n\nUSER QUESTION: " + request.user_question
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"answer": response.content[0].text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI System Error: {e}")

@app.post("/api/briefing")
def generate_briefing(request: BriefingRequest):
    """Generates the morning AI briefing, customized to the user's portfolio."""
    articles = get_articles(limit=15)
    headlines = "\n".join(f"- [{a['sentiment']}][{a['sector']}] {a['title']}" for a in articles)
    
    if request.portfolio_context:
        prompt = (
            f"CRITICAL: The client's portfolio is: {request.portfolio_context}\n\n"
            "Write exactly 5 short bullet points summarizing key market themes based on the headlines. "
            "Evaluate how the news impacts their specific holdings, calculating an [Impact Score: 1-10] for affected holdings.\n"
            "Headlines:\n" + headlines
        )
    else:
        prompt = (
            "Write exactly 5 short bullet points summarizing key market themes, risks, and opportunities based on the headlines. "
            "Start with a bold theme label like **Macro:** or **Risk:**.\n"
            "Headlines:\n" + headlines
        )

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        bullets = [l.strip().lstrip("-•* ") for l in msg.content[0].text.strip().split("\n") if l.strip()]
        return {"briefing": bullets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))