"""
api/main.py — entrypoint for running the real API server.

    uvicorn capretrieve.api.main:app --reload

Requires OPENROUTER_API_KEY to be set (env or .env file) — see
.env.example. WEB_SEARCH_API_KEY is optional; without it the web
connector runs in Tavily's keyless mode (heavily rate-limited).
"""

from __future__ import annotations

from capretrieve.bootstrap import build_default_app

app = build_default_app()