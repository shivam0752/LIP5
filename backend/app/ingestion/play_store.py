"""
play_store.py — Play Store scraper + iOS simulation dataset.

Fetches up to 200 newest Android reviews for the Groww package and merges
25 pre-authored realistic iOS reviews, all filtered to [start_date, end_date].

Corpus schema (every item conforms to):
  { rating, review_title, review_text, date, platform }
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Any

from google_play_scraper import Sort, reviews as gps_reviews

from app.config import get_settings

# ── iOS simulation dataset ─────────────────────────────────────────────────────
# 25 realistic Groww iOS reviews based on real complaint/praise patterns.

_IOS_REVIEWS: list[dict[str, Any]] = [
    {"rating": 2, "review_title": "Options orders keep slipping", "review_text": "Every time I place a limit order for options, it gets filled at a worse price. This never happened on desktop. The mobile app has serious latency issues during market open hours."},
    {"rating": 1, "review_title": "UPI deposit failed, money deducted", "review_text": "Tried adding funds via UPI. The money was deducted from my bank but never credited to Groww. Raised a ticket 3 days ago — still no resolution. Extremely frustrating."},
    {"rating": 3, "review_title": "KYC re-verification loop", "review_text": "Asked to do re-KYC even though I completed it last month. The selfie upload keeps failing with a vague error message. Support just keeps asking me to retry."},
    {"rating": 1, "review_title": "App crashes at 9:15 AM every day", "review_text": "Without fail, the app freezes right when the market opens. I missed a critical trade because of this crash. Has been happening since the last update two weeks ago."},
    {"rating": 2, "review_title": "Support bot is useless", "review_text": "The chatbot cannot understand anything beyond basic queries. When I escalate to a human, wait time is 45+ minutes. Other brokers respond within minutes."},
    {"rating": 5, "review_title": "Best investing app in India", "review_text": "Super clean interface, fast execution, great mutual fund options. The SIP feature works flawlessly. Highly recommend Groww to anyone starting their investment journey."},
    {"rating": 4, "review_title": "Good app but iOS needs polish", "review_text": "The Android version seems more polished than iOS. A few UI elements are misaligned and the chart tooltip behaves oddly on iPhone 15 Pro. Otherwise great product."},
    {"rating": 1, "review_title": "Funds withdrawal delayed 5 days", "review_text": "My withdrawal request has been pending for 5 days. The status just says 'Processing'. No updates from support. I need these funds urgently."},
    {"rating": 2, "review_title": "PAN verification keeps rejecting", "review_text": "I've uploaded my PAN card 4 times in different lighting and orientations. It keeps saying 'document not clear'. My PAN is perfectly readable. This onboarding experience is terrible."},
    {"rating": 3, "review_title": "Chart mismatch with actual LTP", "review_text": "The candlestick chart shows a different LTP than the order book. This mismatch confused me into placing a wrong order. Please fix the real-time data sync."},
    {"rating": 5, "review_title": "Seamless SIP setup", "review_text": "Setting up SIPs is incredibly smooth. The fund comparison feature helped me pick the right fund. Transaction history is well-organized. Five stars!"},
    {"rating": 1, "review_title": "Account frozen without notice", "review_text": "Woke up to find my account frozen. No email, no in-app notification explaining why. I have active positions! This is completely unacceptable. Calling support but can't get through."},
    {"rating": 2, "review_title": "Delayed limit order execution", "review_text": "I placed a buy limit order at 9:16 AM. It sat pending for 20 minutes even though the price crossed my limit multiple times. By the time it executed, the price had moved significantly."},
    {"rating": 4, "review_title": "Great for mutual funds", "review_text": "If you're into mutual funds, this is the app. SIP management, NAV tracking, portfolio analysis — all excellent. Stock trading could use some improvement though."},
    {"rating": 1, "review_title": "UPI ID not recognized", "review_text": "My bank's UPI handle is not recognized by Groww even though it works on every other app. I've been unable to add funds for a week now."},
    {"rating": 2, "review_title": "Support ticket ignored for a week", "review_text": "Opened a ticket about an incorrect transaction on Day 1. It's now Day 7 and the only response I got was an automated acknowledgement. The issue is still unresolved."},
    {"rating": 5, "review_title": "Portfolio tracking is top-notch", "review_text": "The consolidated portfolio view across stocks, mutual funds, and gold is amazing. XIRR calculation is accurate. Best wealth management interface I've used."},
    {"rating": 1, "review_title": "App update broke biometric login", "review_text": "After the latest iOS update, Face ID stopped working. I have to enter my password every single time. Reported this a week ago with no fix in sight."},
    {"rating": 3, "review_title": "Onboarding took 4 days", "review_text": "The KYC verification process took 4 days when competitors do it in hours. The video KYC step kept timing out and I had to reschedule multiple times."},
    {"rating": 2, "review_title": "Settlement cycle confusion", "review_text": "There's no clear explanation of T+1 vs T+2 settlement in the app. I sold shares expecting funds by next day but they came two days later. Need better in-app education."},
    {"rating": 4, "review_title": "Clean dark mode", "review_text": "The new dark mode looks fantastic on OLED. Watchlist management is very intuitive. Just wish the news feed loaded faster."},
    {"rating": 1, "review_title": "Options P&L shows wrong values", "review_text": "My options P&L in the portfolio section shows a completely wrong value. The individual positions are correct but the aggregate is off by lakhs. This is very alarming."},
    {"rating": 2, "review_title": "Aadhaar OTP never arrives", "review_text": "During re-KYC, the Aadhaar OTP is supposed to arrive from UIDAI. It never comes on time — usually 10-15 minutes late and often expired. Please look into this."},
    {"rating": 5, "review_title": "Instant fund credit via NEFT", "review_text": "Added funds via NEFT and they were credited within 30 minutes. Execution speed for large orders is excellent. Groww has improved massively over the last year."},
    {"rating": 3, "review_title": "Watchlist sync issues", "review_text": "My watchlist doesn't sync between my iPhone and iPad. I add a stock on one device and it doesn't show up on the other. Minor but annoying for an otherwise great app."},
]


def fetch_reviews(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """
    Fetch up to 200 newest Android Play Store reviews filtered to [start_date, end_date],
    then merge 25 simulated iOS reviews spread randomly across the same window.

    If no live Android reviews are found (e.g. historical range), falls back to
    loading and spreading reviews from the local sample_reviews.csv.
    """
    settings = get_settings()
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    android_reviews = _fetch_android_reviews(settings.groww_package_name, start, end)

    if not android_reviews:
        from app.storage.store import append_log
        append_log(
            f"No live Play Store reviews found in range {start_date} to {end_date}. "
            "Falling back to simulated CSV reviews dataset.",
            level="WARNING"
        )
        csv_reviews = _load_csv_reviews()
        if csv_reviews:
            android_pool = [r for r in csv_reviews if r["platform"].lower() == "android"]
            ios_pool = [r for r in csv_reviews if r["platform"].lower() == "ios"]
            android_reviews = _spread_reviews(android_pool, start, end, "Android")
            ios_reviews = _spread_reviews(ios_pool, start, end, "iOS")
            return android_reviews + ios_reviews

    ios_reviews = _spread_ios_reviews(start, end)
    return android_reviews + ios_reviews


def _load_csv_reviews() -> list[dict[str, Any]]:
    """Try to load sample reviews from CSV file in multiple possible paths."""
    import csv
    possible_paths = [
        Path(__file__).resolve().parents[3] / "docs" / "sample_reviews.csv",
        Path("docs/sample_reviews.csv"),
        Path("../docs/sample_reviews.csv"),
        Path("backend/docs/sample_reviews.csv"),
    ]
    csv_path = None
    for p in possible_paths:
        if p.exists():
            csv_path = p
            break
    if not csv_path:
        return []

    reviews = []
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    reviews.append({
                        "rating": int(row["rating"]),
                        "review_title": row["review_title"].strip(),
                        "review_text": row["review_text"].strip(),
                        "platform": row["platform"].strip(),
                    })
                except (KeyError, ValueError):
                    continue
    except Exception as exc:
        # Avoid logger import cycle
        print(f"Failed to load sample reviews from CSV: {exc}")
    return reviews


def _fetch_android_reviews(
    package_name: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    """Fetch Android reviews recursively until we cover the entire date window."""
    result: list[dict[str, Any]] = []
    continuation_token = None
    
    batch_size = 100
    max_total = 1000  # Safety cap to avoid infinite loops or huge payloads
    total_fetched = 0
    
    while total_fetched < max_total:
        try:
            if continuation_token:
                raw, continuation_token = gps_reviews(
                    package_name,
                    continuation_token=continuation_token
                )
            else:
                raw, continuation_token = gps_reviews(
                    package_name,
                    lang="en",
                    country="in",
                    sort=Sort.NEWEST,
                    count=batch_size,
                )
        except Exception as exc:
            if result:
                break
            raise RuntimeError(f"google-play-scraper failed: {exc}") from exc

        if not raw:
            break

        total_fetched += len(raw)
        has_older_dates = False

        for r in raw:
            review_date: datetime = r.get("at")
            if review_date is None:
                continue
            d = review_date.date() if isinstance(review_date, datetime) else review_date
            
            # Since reviews are sorted from newest to oldest, if we see a date older
            # than the start date, we can stop fetching further batches.
            if d < start:
                has_older_dates = True

            if start <= d <= end:
                result.append({
                    "rating": int(r.get("score", 0)),
                    "review_title": (r.get("title") or "").strip(),
                    "review_text": (r.get("content") or "").strip(),
                    "date": d.isoformat(),
                    "platform": "Android",
                })

        if has_older_dates or not continuation_token:
            break

    return result


def _spread_reviews(pool: list[dict[str, Any]], start: date, end: date, platform: str) -> list[dict[str, Any]]:
    """Spread a pool of reviews randomly across the date range."""
    window_days = (end - start).days
    result: list[dict[str, Any]] = []
    for review in pool:
        offset = random.randint(0, max(window_days, 0))
        assigned_date = start + timedelta(days=offset)
        result.append({
            "rating": review["rating"],
            "review_title": review["review_title"],
            "review_text": review["review_text"],
            "date": assigned_date.isoformat(),
            "platform": platform,
        })
    return result


def _spread_ios_reviews(start: date, end: date) -> list[dict[str, Any]]:
    """Assign random dates within [start, end] to the 25 pre-authored iOS reviews."""
    return _spread_reviews(_IOS_REVIEWS, start, end, "iOS")

