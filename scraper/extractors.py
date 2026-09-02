"""
Contact Information Extractors & Search Enrichment
Extracts and sanitizes phone numbers, email addresses, and social media handles from web pages and search engines.
"""

import re
import urllib.parse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

# Directories and aggregate platforms to ignore when looking for official website
DIRECTORY_DOMAINS = [
    'yelp.com', 'tripadvisor.com', 'wikipedia.org', 'doordash.com',
    'ubereats.com', 'grubhub.com', 'postmates.com', 'opentable.com',
    'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
    'youtube.com', 'pinterest.com', 'mapquest.com', 'yellowpages.com',
    'toasttab.com', 'toast.app', 'ezcater.com', 'order.online', 'seamless.com',
    'restaurantji.com', 'restaurantjump.com', 'zomato.com', 'menupix.com'
]

# Common fake / non-contact email patterns to ignore
BLACKLIST_EMAIL_PATTERNS = [
    'example.com', 'test.com', 'email.com', 'youremail', 'your@',
    'sentry.io', 'wixpress.com', 'placeholder', 'noreply',
    'donotreply', 'no-reply', 'sentry-next', 'protection',
    'cloudflare', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    '.css', '.js', 'schema.org', 'w3.org', 'googleapis',
    'domain.com', 'sample.com', 'mywebsite.com', 'user@'
]

# Patterns for US and International phone numbers
PHONE_PATTERNS = [
    r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',
    r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
    r'\b\d{10}\b'
]


def clean_phone(phone: str) -> str | None:
    """Normalize and validate a detected phone number."""
    if not phone:
        return None
    phone = phone.strip()
    phone = re.sub(r'^tel:', '', phone, flags=re.IGNORECASE)
    phone = phone.replace('\xa0', ' ').strip()
    digits = re.sub(r'\D', '', phone)

    if 10 <= len(digits) <= 15:
        if len(set(digits)) <= 2:
            return None
        return phone
    return None


def clean_email(email: str) -> str | None:
    """Validate and sanitize an extracted email address."""
    if not email:
        return None
    email = email.strip().lower()
    email = re.sub(r'^mailto:', '', email)
    email = urllib.parse.unquote(email)
    email = email.split('?')[0].strip()

    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        for pattern in BLACKLIST_EMAIL_PATTERNS:
            if pattern in email:
                return None
        return email
    return None


def extract_phones_from_text(text: str) -> set[str]:
    """Extract all valid phone numbers found within raw text."""
    phones = set()
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            cleaned = clean_phone(m)
            if cleaned:
                phones.add(cleaned)
    return phones


def extract_emails_from_text(text: str) -> set[str]:
    """Extract all valid email addresses found within raw text."""
    emails = set()
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    for m in matches:
        cleaned = clean_email(m)
        if cleaned:
            emails.add(cleaned)
    return emails


def extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, set[str]]:
    """Extract Facebook, Instagram, LinkedIn, and X/Twitter links from BeautifulSoup object."""
    social = {
        'facebook': set(),
        'instagram': set(),
        'linkedin': set(),
        'twitter': set()
    }

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        href_lower = href.lower()

        if 'facebook.com/' in href_lower and not any(x in href_lower for x in ['/sharer', '/share', '/dialog', '/tr?']):
            social['facebook'].add(href)
        elif 'instagram.com/' in href_lower and not any(x in href_lower for x in ['/share', '/p/']):
            social['instagram'].add(href)
        elif 'linkedin.com/' in href_lower and not any(x in href_lower for x in ['/share', '/sharing']):
            social['linkedin'].add(href)
        elif ('twitter.com/' in href_lower or 'x.com/' in href_lower) and not any(x in href_lower for x in ['/intent', '/share']):
            social['twitter'].add(href)

    return social


def find_subpage_links(soup: BeautifulSoup, base_url: str, max_links: int = 4) -> list[str]:
    """Find internal links to relevant subpages (Contact, About, Location, Locations, Hours)."""
    subpage_keywords = ['contact', 'about', 'location', 'hours', 'find-us', 'reach-us', 'info', 'menu']
    links = set()
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        href_lower = href.lower()
        text_lower = a.get_text().lower().strip()

        if any(kw in href_lower for kw in subpage_keywords) or any(kw in text_lower for kw in subpage_keywords):
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == base_domain and full_url != base_url:
                links.add(full_url)
                if len(links) >= max_links:
                    break

    return list(links)


def search_restaurant_online(name: str, location: str = "Houston, TX", session: requests.Session = None, timeout: int = 10) -> dict:
    """
    Query search engines (using DDGS with browser TLS fingerprinting) to:
    1. Automatically discover the official restaurant website
    2. Extract phone numbers and emails directly from snippets
    3. Discover official Facebook, Instagram, and LinkedIn profiles
    """
    result = {
        'discovered_url': None,
        'phones': set(),
        'emails': set(),
        'social': {'facebook': set(), 'instagram': set(), 'linkedin': set(), 'twitter': set()}
    }

    query = f"{name} {location}"

    if DDGS:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=6))
                for r in results:
                    href = r.get('href', '').strip()
                    title = r.get('title', '')
                    body = r.get('body', '')

                    # Extract phones & emails directly from snippet text
                    combined_text = f"{title} {body}"
                    result['phones'].update(extract_phones_from_text(combined_text))
                    result['emails'].update(extract_emails_from_text(combined_text))

                    # Parse URLs
                    domain = urlparse(href).netloc.lower()
                    if 'facebook.com' in domain and not any(x in href.lower() for x in ['/sharer', '/share']):
                        result['social']['facebook'].add(href)
                    elif 'instagram.com' in domain and '/p/' not in href:
                        result['social']['instagram'].add(href)
                    elif 'linkedin.com' in domain:
                        result['social']['linkedin'].add(href)
                    elif not any(d in domain for d in DIRECTORY_DOMAINS) and not result['discovered_url']:
                        result['discovered_url'] = href

        except Exception:
            pass

    return result


def scrape_social_profile(url: str, session: requests.Session, timeout: int = 8) -> dict:
    """Extract contact phone/email from Facebook page or Instagram bio."""
    result = {'phones': set(), 'emails': set()}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Check og:description meta tag which commonly contains phone/email
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                desc_text = og_desc['content']
                result['phones'].update(extract_phones_from_text(desc_text))
                result['emails'].update(extract_emails_from_text(desc_text))

            page_text = soup.get_text(separator=' ')
            result['phones'].update(extract_phones_from_text(page_text))
            result['emails'].update(extract_emails_from_text(page_text))
    except Exception:
        pass
    return result
