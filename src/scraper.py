import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
from google_play_scraper import reviews, Sort
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# App Configurations
PLAY_STORE_APP_ID = "com.nextbillion.groww"
APP_STORE_APP_ID = "1322319882"
DEFAULT_LOOKBACK_DAYS = 70  # 10 weeks recommendation

def clean_pii(text):
    """
    Scrubs PII (Emails, Phone numbers, long digits/account numbers, UPI IDs) from text.
    """
    if not isinstance(text, str):
        return ""
    
    # 1. Clean Emails
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, "[EMAIL]", text)
    
    # 2. Clean UPI IDs
    upi_pattern = r'[a-zA-Z0-9.\-_]+@[a-zA-Z]{2,}'
    text = re.sub(upi_pattern, "[UPI]", text)
    
    # 3. Clean Phone numbers (common Indian formats)
    phone_pattern = r'(?:\+?91[\-\s]?)?[6-9]\d{9}|\b\d{5}[\-\s]?\d{5}\b'
    text = re.sub(phone_pattern, "[PHONE]", text)
    
    # 4. Clean Account Numbers / Customer IDs / generic long numeric values (6 to 16 digits)
    acc_pattern = r'\b\d{6,16}\b'
    text = re.sub(acc_pattern, "[ID]", text)
    
    return text

def scrape_play_store(max_count=300):
    """
    Scrapes reviews from Google Play Store for Groww.
    """
    print(f"Scraping Google Play Store reviews for {PLAY_STORE_APP_ID}...")
    try:
        # Fetch reviews
        result, _ = reviews(
            PLAY_STORE_APP_ID,
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=max_count
        )
        
        scraped_reviews = []
        for r in result:
            scraped_reviews.append({
                'rating': int(r.get('score', 0)),
                'title': '',  # Play Store reviews don't have separate titles
                'review_text': r.get('content', ''),
                'date': r.get('at'),
                'platform': 'google_play'
            })
        print(f"Successfully scraped {len(scraped_reviews)} reviews from Google Play Store.")
        return scraped_reviews
    except Exception as e:
        print(f"Error scraping Google Play Store: {e}")
        return []

def scrape_app_store(max_pages=10):
    """
    Scrapes reviews from Apple App Store RSS feed for Groww.
    """
    print(f"Scraping Apple App Store reviews for ID {APP_STORE_APP_ID}...")
    scraped_reviews = []
    
    # Namespaces used in Apple XML feed
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'im': 'http://itunes.apple.com/rss'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={APP_STORE_APP_ID}/sortby=mostrecent/xml"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch App Store page {page}: Status code {response.status_code}")
                break
                
            root = ET.fromstring(response.content)
            entries = root.findall('atom:entry', ns)
            
            # The first entry in RSS is typically application info metadata, not a review
            if page == 1 and entries:
                entries = entries[1:]
                
            if not entries:
                break
                
            for entry in entries:
                rating_elem = entry.find('im:rating', ns)
                title_elem = entry.find('atom:title', ns)
                content_elem = entry.find('atom:content', ns)
                updated_elem = entry.find('atom:updated', ns)
                
                if content_elem is None or rating_elem is None:
                    continue
                    
                rating = int(rating_elem.text) if rating_elem.text else 0
                title = title_elem.text if title_elem is not None else ""
                content = content_elem.text if content_elem is not None else ""
                
                # Parse RSS date: e.g. "2026-06-08T05:22:12-07:00"
                date_str = updated_elem.text if updated_elem is not None else ""
                date_val = None
                if date_str:
                    try:
                        # Strip colon from timezone offset to parse with python datetime if needed
                        # Or simply parse standard ISO formats
                        date_val = datetime.fromisoformat(date_str)
                    except ValueError:
                        date_val = datetime.now(timezone.utc)
                else:
                    date_val = datetime.now(timezone.utc)
                
                scraped_reviews.append({
                    'rating': rating,
                    'title': title,
                    'review_text': content,
                    'date': date_val,
                    'platform': 'app_store'
                })
        except Exception as e:
            print(f"Error parsing App Store feed page {page}: {e}")
            break
            
    print(f"Successfully scraped {len(scraped_reviews)} reviews from Apple App Store.")
    return scraped_reviews

def generate_mock_reviews(lookback_days):
    """
    Generates high-quality realistic mock reviews for fallback or testing.
    """
    print("Generating fallback mock reviews...")
    mock_templates = [
        # Onboarding & KYC
        {"rating": 1, "title": "KYC verification pending", "text": "My KYC document verification is stuck since 4 days. Please resolve it soon. Support is not replying to ticket 987654.", "platform": "google_play"},
        {"rating": 2, "title": "Aadhar OTP not received", "text": "Trying to complete my e-sign for onboarding but not getting any OTP on registered number. Phone is 9876543210. Fix this error.", "platform": "app_store"},
        {"rating": 5, "title": "Super fast onboarding", "text": "Opened my account in under 10 minutes. Fully digital process and very smooth UI. Loving Groww so far!", "platform": "google_play"},
        
        # Payments & Deposits
        {"rating": 2, "title": "UPI Deposit failed", "text": "Money got deducted from my HDFC bank account via UPI but not credited to Groww balance. Checked my balance and it shows pending status. Emailed support at support@groww.in.", "platform": "google_play"},
        {"rating": 1, "title": "Bank link issues", "text": "Not able to link my SBI savings account. Getting error transaction failed constantly. Very disappointed.", "platform": "app_store"},
        {"rating": 4, "title": "Smooth deposits", "text": "Deposits are instant via Net Banking, but UPI sometimes delays a bit. Overall nice experience.", "platform": "google_play"},
        
        # Portfolio & Statements
        {"rating": 3, "title": "Statement missing details", "text": "Downloaded my capital gains statement but some mutual fund holdings are not matching. Need accurate reports.", "platform": "google_play"},
        {"rating": 5, "title": "Excellent portfolio tracker", "text": "The P&L dashboard and graph visualization are very intuitive. Easy to track my daily returns.", "platform": "app_store"},
        
        # Withdrawals & Redemptions
        {"rating": 1, "title": "Withdrawal stuck", "text": "Requested withdrawal of Rs 15000 to my account on Friday. Today is Tuesday and status is still in process. Account number 5020000412345.", "platform": "google_play"},
        {"rating": 2, "title": "Redemption takes long", "text": "Mutual fund redemption takes too many days compared to other apps. Please speed up withdrawal times.", "platform": "app_store"},
        
        # App Stability & UX
        {"rating": 1, "title": "Crash after update", "text": "The app keeps crashing on my iPhone 14 after the latest update today. Cannot login to check my portfolio.", "platform": "app_store"},
        {"rating": 5, "title": "Clean interface", "text": "Minimalist design, fast loading, dark mode works beautifully. Best app for mutual fund and stock investing.", "platform": "google_play"},
        {"rating": 2, "title": "App very slow", "text": "Opening the watchlist takes ages. Lagging on stock charts page.", "platform": "google_play"}
    ]
    
    # Replicate templates over the lookback period to create realistic bulk data
    mock_reviews = []
    now = datetime.now(timezone.utc)
    
    # Create ~65 mock entries spread out over the past weeks
    for i in range(65):
        template = mock_templates[i % len(mock_templates)]
        # Random offset within lookback days
        days_ago = (i * 1.1) % lookback_days
        review_date = now - timedelta(days=days_ago)
        
        # Add slight modifications to make them distinct
        text_variation = template["text"]
        if i > len(mock_templates):
            text_variation += f" (Ref ID: {100000 + i})"
            
        mock_reviews.append({
            'rating': template["rating"],
            'title': template["title"],
            'review_text': text_variation,
            'date': review_date,
            'platform': template["platform"]
        })
        
    return mock_reviews

def run_scraper(lookback_days=DEFAULT_LOOKBACK_DAYS, force_mock=False):
    """
    Main entry point to fetch, clean, and store reviews.
    """
    all_reviews = []
    
    if not force_mock:
        # Try real scraping
        play_reviews = scrape_play_store()
        app_reviews = scrape_app_store()
        all_reviews = play_reviews + app_reviews
        
    # If scraping failed, returned empty, or force_mock is active, use mock fallback
    if not all_reviews:
        print("No live reviews collected (or mock mode enabled). Falling back to mock review dataset.")
        all_reviews = generate_mock_reviews(lookback_days)
        
    # Create DataFrame
    df = pd.DataFrame(all_reviews)
    
    # 1. Standardize and parse dates
    df['date'] = pd.to_datetime(df['date'], utc=True)
    
    # 2. Filter by Date (last N days)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    df = df[df['date'] >= cutoff_date]
    
    # 3. Clean PII on both title and review_text
    df['title'] = df['title'].apply(clean_pii)
    df['review_text'] = df['review_text'].apply(clean_pii)
    
    # 4. Deduplicate on standard fields
    df = df.drop_duplicates(subset=['rating', 'title', 'review_text', 'platform'])
    
    # 5. Sort by date newest first
    df = df.sort_values(by='date', ascending=False)
    
    # Ensure directory exists
    os.makedirs('data', exist_ok=True)
    
    # Save output
    output_path = 'data/reviews_raw.csv'
    df.to_csv(output_path, index=False)
    
    print(f"Phase 1 Ingestion Complete. Saved {len(df)} cleaned reviews to '{output_path}'.")
    return output_path

if __name__ == '__main__':
    # Test run
    run_scraper()
