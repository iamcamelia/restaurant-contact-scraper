# 🍽️ Restaurant Contact Scraper & Web App

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Requests](https://img.shields.io/badge/requests-HTTP-orange.svg)](https://requests.readthedocs.io/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-brightgreen.svg)](https://www.crummy.com/software/BeautifulSoup/)

A powerful, full-stack **Restaurant Contact Scraper & Web Application** engineered to discover **verified phone numbers**, **email addresses**, and **social media profiles** (Facebook, Instagram, LinkedIn, X/Twitter) from restaurant websites, subpages, social media bios, and search engine snippets.

Includes both a **sleek web dashboard** and a **high-throughput CLI engine**, complete with instant 1-click **Google Sheets** synchronization.

---

## 🌟 What It Does

1. 🌐 **Official Website Scraping**: Crawls homepage, header, footer, `tel:`, and `mailto:` links.
2. 🔍 **Automatic Subpage Traversal**: Inspects `/contact`, `/about`, `/locations`, and `/hours` pages to catch buried contact details.
3. 📱 **Social Media Bio & Profile Extraction**: Deep-inspects Facebook page about sections and Instagram bios to extract numbers and emails.
4. 🔎 **Search Engine Fallback Enrichment**: Queries Bing/Google search snippets to fill in missing details if the website doesn't display an email or phone directly.
5. 📊 **1-Click Google Sheets Integration**: Features a button to copy formatted TSV rows ready to paste straight into **Columns G (Number)** and **H (Email)** of your Google Sheet.

---

## 🚀 Run the Web App (Recommended)

Start the web interface locally with a single command:

```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Launch the Web Application
python app.py
```

Then open your browser to **`http://127.0.0.1:5000`**.

### Web App Features:
- ⚡ **Quick Single Scraper**: Type any restaurant name and URL (e.g. *Paradise HTX*, *https://theparadisehtx.com/*) to instantly get its phone, email, and social links with 1-click copy buttons.
- 📋 **Bulk Batch Scraper**: Paste a list of `Name, URL` pairs or upload a CSV file. Watch the live progress bar and get a downloadable table.
- 🏙️ **Houston 110 Dataset Explorer**: Pre-loaded with all 110 Houston TX restaurants from your spreadsheet, filterable by *Has Phone*, *Has Email*, and *Has Socials*.
- 📋 **Copy for Google Sheets (Cols G & H)**: Formats all contacts for direct copy-pasting into cell G6 of your spreadsheet.
- 💾 **Export Data**: Download CSV, JSON, or a ready-to-run `.gs` Google Apps Script.

---

## 💻 CLI Usage (Command Line)

You can also run the scraper directly from your terminal:

```bash
# Scrape a single restaurant website
python main.py --url "https://theparadisehtx.com/" --name "Paradise HTX"

# Batch scrape any CSV file with 8 worker threads
python main.py --input restaurants.csv --workers 8 --output results.csv --json results.json

# Run on the included Houston 110 restaurants dataset and generate Google Sheets script
python main.py --houston --workers 8 --output data/houston_results.csv --generate-apps-script
```

### CLI Options

| Flag | Shorthand | Description |
|---|---|---|
| `--input` | `-i` | Path to CSV/JSON input file |
| `--url` | `-u` | Single restaurant URL to scrape |
| `--name` | `-n` | Restaurant name for single URL mode |
| `--output` | `-o` | Output CSV path (default: `output_contacts.csv`) |
| `--json` | | Output JSON path |
| `--workers` | `-w` | Concurrent worker threads (default: 5) |
| `--houston` | | Run pre-configured Houston 110 restaurants |
| `--generate-apps-script` | | Output ready-to-run Google Apps Script for Sheets |

---

## 📑 Google Sheets 1-Click Sync Guide

To populate your Google Spreadsheet columns:

### Method A: Direct Paste (Fastest)
1. Open the Web App (`python app.py` -> `http://127.0.0.1:5000`).
2. Click **Copy for Google Sheets (Cols G & H)**.
3. Open your [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1JuwoecMCUhPfWbhiLtq7l0sGtJ312mzMmNcbs5sp27U/edit?gid=0#gid=0).
4. Click cell **G6** and press **Ctrl+V** (or Cmd+V on Mac). All phones and emails will populate into Columns G & H!

### Method B: Google Apps Script
1. In your spreadsheet, open **Extensions** > **Apps Script**.
2. Paste the contents of [`data/update_google_sheet.gs`](data/update_google_sheet.gs).
3. Click **Run** (`fillRestaurantContacts`) — it automatically fills Columns G & H for all 110 rows!

---

## ☁️ Free Cloud Deployment (Render / Railway / Docker)

The repository includes a `Procfile` and `Dockerfile` for deployment:

### Deploy to Render / Railway:
1. Connect your GitHub repository: `iamcamelia/restaurant-contact-scraper`
2. Environment: **Python 3**
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`

### Run with Docker:
```bash
docker build -t restaurant-scraper .
docker run -p 5000:5000 restaurant-scraper
```

---

## 📂 Project Structure

```
restaurant-contact-scraper/
├── app.py                    # Flask Web Application backend
├── templates/
│   └── index.html            # Web app frontend interface (Tailwind CSS)
├── static/
│   ├── app.js                # Frontend interactive logic & API connectors
│   └── style.css             # Custom styles & social badges
├── scraper/
│   ├── __init__.py           # Package exports
│   ├── core.py               # Multithreaded scraping engine
│   └── extractors.py         # Regex filters, cleaning & social media extractors
├── data/
│   ├── houston_restaurants.csv          # 110 Houston input list
│   ├── houston_restaurants_scraped.csv  # Completed scraped output
│   ├── houston_restaurants_scraped.json # Full JSON export
│   └── update_google_sheet.gs          # 1-click Google Apps Script
├── main.py                   # CLI runner
├── requirements.txt          # Python dependencies (flask, requests, bs4, tqdm)
├── Dockerfile                # Container deployment setup
├── Procfile                  # Cloud web deployment config
├── .gitignore
├── LICENSE                   # MIT License
└── README.md                 # Complete documentation
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) — created for Camelia Hossain (`iamcamelia`).
