# 🍽️ Restaurant Contact Scraper & Web App (AI Powered)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-purple.svg)](https://ai.google.dev/)
[![Schema.org](https://img.shields.io/badge/Data-Schema.org%20JSON--LD-brightgreen.svg)](https://schema.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent, multi-source **Restaurant Contact Scraper & Web Application** powered by **Google Gemini 2.5 Flash AI** and free open web resources. Designed to discover **verified phone numbers**, **email addresses**, **physical street addresses**, and **official social media profiles** (Facebook, Instagram, LinkedIn, X/Twitter) from restaurant websites, search snippets, Schema.org metadata, and social pages.

---

## ⚡ Multi-Source Free Pipeline

1. 🤖 **Gemini 2.5 Flash AI Layer**:
   - Parses noisy text and search snippets with high-precision contextual reasoning.
   - Detects the exact branch/street phone number when multiple locations exist (e.g. *6th Street* branch).
   - Eliminates spam bot-traps, placeholder numbers, and web designer credit emails (`info@squarespace.com`, `support@wix.com`).
   - Assigns an **AI Confidence Score** (*High / Medium / Low*) and explanatory notes for each extraction.
2. 🔍 **Automatic Website & Social Discovery**:
   - Leave the Website URL empty — the scraper queries search engines (DuckDuckGo Lite) to automatically find the official website, Facebook page, and Instagram profile.
3. 📑 **Schema.org JSON-LD & OpenGraph Metadata**:
   - Parses `<script type="application/ld+json">` to extract owner-published telephone numbers, emails, addresses, and `sameAs` links directly from the website's source code.
4. 📄 **Subpage Crawling**:
   - Automatically navigates `/locations`, `/contact`, `/about`, and `/hours` pages.
5. 📱 **Social Profile Deep Inspection**:
   - Inspects public Facebook About sections and Instagram bios to grab contact info.
6. 📊 **1-Click Google Sheets Integration**:
   - **"Copy for Google Sheets (Cols G & H)"**: Formats all phones and emails for instant copy-pasting into cell **G6** of your spreadsheet.

---

## 🚀 Quick Start (Web Application)

```bash
# 1. Clone the repository
git clone https://github.com/iamcamelia/restaurant-contact-scraper.git
cd restaurant-contact-scraper

# 2. Install requirements
pip install -r requirements.txt

# 3. Launch the web dashboard
python app.py
```

Then open your browser to **`http://127.0.0.1:5000`**.

> **1-Click Windows Launcher:** You can also simply double-click [`run_website.bat`](run_website.bat) to start the server and open your browser automatically.

---

## 💻 CLI Usage

```bash
# Scrape a restaurant with AI validation (auto-discovering website):
python main.py --name "happy chicks 6th street" --location "Austin, TX"

# Scrape a known URL:
python main.py --url "https://theparadisehtx.com/" --name "Paradise HTX"

# Batch scrape any CSV file with 8 worker threads:
python main.py --input my_restaurants.csv --workers 8 --output results.csv

# Run without AI (heuristic only):
python main.py --name "Time Pizza" --no-ai
```

---

## ⚙️ AI Configuration

The application automatically uses the `GEMINI_API_KEY` from your environment if present.

To set or customize your free Gemini API key:
- **In the Web App:** Click the **AI Settings** gear icon in the top header and paste your key.
- **In the Terminal:**
  ```bash
  # Windows PowerShell
  $env:GEMINI_API_KEY="your_api_key_here"
  
  # Linux / Mac
  export GEMINI_API_KEY="your_api_key_here"
  ```
> Free Gemini API keys can be generated at [Google AI Studio](https://aistudio.google.com/).

---

## 📂 Project Structure

```
restaurant-contact-scraper/
├── app.py                    # Flask Web App backend with AI endpoints
├── templates/
│   └── index.html            # Frontend UI (Tailwind CSS, AI status & modal)
├── static/
│   ├── app.js                # Frontend logic (AI settings, copy actions, tables)
│   └── style.css             # UI styling & badges
├── scraper/
│   ├── __init__.py           # Package exports
│   ├── ai.py                 # Google Gemini 2.5 Flash extraction & validation
│   ├── core.py               # Multi-source scraper engine
│   └── extractors.py         # Schema.org, regex cleaning & search discovery
├── data/
│   ├── houston_restaurants.csv          # 110 Houston input list
│   ├── houston_restaurants_scraped.csv  # Completed scraped output
│   ├── houston_restaurants_scraped.json # Full JSON export
│   └── update_google_sheet.gs          # 1-click Google Apps Script
├── main.py                   # CLI runner
├── run_website.bat           # 1-click Windows launcher
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container deployment
├── Procfile                  # Cloud deployment
├── LICENSE                   # MIT License
└── README.md                 # Documentation
```

---

## 📜 License

Distributed under the [MIT License](LICENSE).
