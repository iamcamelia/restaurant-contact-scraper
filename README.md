# 🍽️ Restaurant Contact Scraper & Lead Generator

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Requests](https://img.shields.io/badge/requests-HTTP-orange.svg)](https://requests.readthedocs.io/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-brightgreen.svg)](https://www.crummy.com/software/BeautifulSoup/)

A fast, multithreaded Python scraper engineered to extract **phone numbers**, **email addresses**, and **social media profiles** (Facebook, Instagram, LinkedIn, X/Twitter) from restaurant and business websites.

Built with automatic subpage discovery (`/contact`, `/about`, `/locations`), robust phone/email sanitization (filtering spam protections, placeholder emails, and tracking pixels), and instant 1-click **Google Sheets** synchronization.

---

## ⚡ Key Features

- 📞 **Smart Phone Extraction**: Detects US and international formats, tel: links, and unformatted numbers with automatic deduplication.
- ✉️ **Clean Email Extraction**: Identifies mailto: tags and text emails while automatically filtering placeholder emails, media extensions (.png, .jpg), and analytics beacons (sentry, cloudflare, etc.).
- 🌐 **Social Media Detection**: Grabs official profiles across Facebook, Instagram, LinkedIn, and X/Twitter.
- 🔍 **Subpage Crawling**: Traverses internal pages like Contact Us, About, and Locations to uncover hidden contact info.
- 🚀 **High Concurrency**: Multithreaded execution using `concurrent.futures` with configurable worker threads.
- 📊 **Google Sheets Integration**: Automatically generates a ready-to-paste **Google Apps Script** snippet (`update_google_sheet.gs`) to populate spreadsheet columns with a single click.
- 📁 **Export Formats**: Outputs directly to CSV, JSON, or Google Apps Script.

---

## 📦 Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/iamcamelia/restaurant-contact-scraper.git
cd restaurant-contact-scraper
pip install -r requirements.txt
```

---

## 🚀 Quick Start & CLI Usage

### 1. Scrape a Single Restaurant Website
Quickly inspect and test a single restaurant:
```bash
python main.py --url "https://theparadisehtx.com/" --name "Paradise HTX"
```

### 2. Batch Scrape from Any CSV File
Provide any CSV containing restaurant names and URLs:
```bash
python main.py --input my_restaurants.csv --workers 8 --output results.csv --json results.json
```
> **Tip:** The input CSV can have column headers like `name`, `url` (or `Restaurant`, `Website`, `link`).

### 3. Run the Pre-Configured Houston 110 Restaurants Dataset
Includes the 110 Houston restaurants dataset ready to run out-of-the-box:
```bash
python main.py --houston --workers 8 --output data/houston_results.csv --generate-apps-script
```

### Available Command-Line Arguments

| Argument | Shorthand | Description | Default |
|---|---|---|---|
| `--input` | `-i` | Path to input CSV or JSON | None |
| `--url` | `-u` | Single restaurant URL to scrape | None |
| `--name` | `-n` | Restaurant name for single URL mode | "Target Restaurant" |
| `--output` | `-o` | Output CSV file path | `output_contacts.csv` |
| `--json` | | Optional path to export JSON | None |
| `--workers` | `-w` | Concurrent worker threads | `5` |
| `--timeout` | `-t` | HTTP request timeout in seconds | `12` |
| `--houston` | | Run built-in Houston 110 restaurants | False |
| `--generate-apps-script` | | Output Google Apps Script for Sheets | False |

---

## 📑 Google Sheets 1-Click Sync

To populate your Google Spreadsheet (e.g., Column G for Phone, Column H for Email) without manual entry:

1. Open your target Google Sheet in Chrome/your browser.
2. In the top navigation bar, click **Extensions** > **Apps Script**.
3. Clear any existing code in the editor.
4. Copy and paste the contents of `data/update_google_sheet.gs` (or your generated script).
5. Click the **Save** icon, then click **Run** (`fillRestaurantContacts`).
6. Approve permissions when prompted.
7. Switch back to your sheet — all phone numbers and emails will appear instantly in Columns G and H!

---

## 📂 Project Structure

```
restaurant-contact-scraper/
├── scraper/
│   ├── __init__.py           # Package exports
│   ├── core.py               # RestaurantScraper engine (threading, session)
│   └── extractors.py         # Regex filters, cleaning, social media extractors
├── data/
│   ├── houston_restaurants.csv          # Input list (110 Houston TX restaurants)
│   ├── houston_restaurants_scraped.csv  # Completed scraped output
│   ├── houston_restaurants_scraped.json # Full JSON export
│   └── update_google_sheet.gs          # Ready-to-run Google Apps Script
├── main.py                   # Command-line interface
├── requirements.txt          # Python dependencies
├── .gitignore                # Git exclusions
├── LICENSE                   # MIT License
└── README.md                 # Documentation
```

---

## 📊 Houston 110 Restaurants Scraped Dataset Summary

| Metric | Result |
|---|---|
| **Total Restaurants Scraped** | 110 |
| **Phone Numbers Discovered** | 38 restaurants |
| **Emails Discovered** | 24 restaurants |
| **Social Links Discovered** | 45+ restaurants (Facebook, Instagram, LinkedIn) |

*The full dataset is available in [`data/houston_restaurants_scraped.csv`](data/houston_restaurants_scraped.csv).*

---

## 🛠️ Customization & Python Library Usage

You can also import `RestaurantScraper` directly into your own Python scripts:

```python
from scraper import RestaurantScraper

scraper = RestaurantScraper(timeout=10, max_subpages=3)

# Scrape a single restaurant
restaurant_data = scraper.scrape_restaurant("Time Pizza", "https://timepizzahouston.com/")
print(restaurant_data['phone'])
print(restaurant_data['email'])
print(restaurant_data['facebook'])

# Batch scrape a list
items = [
    {"name": "The Nines", "url": "https://theninesthai.com/"},
    {"name": "Paradise HTX", "url": "https://theparadisehtx.com/"}
]
results = scraper.scrape_batch(items, max_workers=4)
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - feel free to use and adapt it for your own research or lead generation projects.
