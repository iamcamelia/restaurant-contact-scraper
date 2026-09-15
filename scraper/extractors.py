"""
Contact Information Extractors & Search Enrichment
Extracts and sanitizes phone numbers, email addresses, and social media handles from web pages,
Schema.org structured data, and search engines.
"""

import json
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


def extract_structured_data(soup: BeautifulSoup) -> dict:
    """Extract Schema.org JSON-LD and OpenGraph contact metadata from page."""
    result = {
        'phones': set(),
        'emails': set(),
        'address': '',
        'social': {'facebook': set(), 'instagram': set(), 'linkedin': set(), 'twitter': set()}
    }

    # 1. Parse Schema.org JSON-LD scripts
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            raw = script.string or ''
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            if isinstance(data, dict) and '@graph' in data:
                items = data['@graph']

            for item in items:
                if not isinstance(item, dict):
                    continue
                # Telephone
                tel = item.get('telephone') or item.get('phone')
                if tel:
                    cleaned = clean_phone(str(tel))
                    if cleaned:
                        result['phones'].add(cleaned)

                # Email
                em = item.get('email')
                if em:
                    cleaned = clean_email(str(em))
                    if cleaned:
                        result['emails'].add(cleaned)

                # Address
                addr = item.get('address')
                if isinstance(addr, dict) and not result['address']:
                    street = addr.get('streetAddress', '')
                    locality = addr.get('addressLocality', '')
                    region = addr.get('addressRegion', '')
                    postal = addr.get('postalCode', '')
                    parts = [p for p in [street, locality, region, postal] if p]
                    if parts:
                        result['address'] = ', '.join(parts)
                elif isinstance(addr, str) and not result['address']:
                    result['address'] = addr

                # SameAs social links
                same_as = item.get('sameAs') or []
                if isinstance(same_as, str):
                    same_as = [same_as]
                for link in same_as:
                    link_lower = str(link).lower()
                    if 'facebook.com' in link_lower:
                        result['social']['facebook'].add(link)
                    elif 'instagram.com' in link_lower:
                        result['social']['instagram'].add(link)
                    elif 'linkedin.com' in link_lower:
                        result['social']['linkedin'].add(link)
                    elif 'twitter.com' in link_lower or 'x.com' in link_lower:
                        result['social']['twitter'].add(link)
        except Exception:
            pass

    # 2. OpenGraph & Meta contact tags
    og_tel = soup.find('meta', property='business:contact_data:phone_number') or soup.find('meta', attrs={'name': 'telephone'})
    if og_tel and og_tel.get('content'):
        cleaned = clean_phone(og_tel['content'])
        if cleaned:
            result['phones'].add(cleaned)

    og_email = soup.find('meta', property='business:contact_data:email') or soup.find('meta', attrs={'name': 'email'})
    if og_email and og_email.get('content'):
        cleaned = clean_email(og_email['content'])
        if cleaned:
            result['emails'].add(cleaned)

    og_street = soup.find('meta', property='business:contact_data:street_address')
    if og_street and og_street.get('content') and not result['address']:
        result['address'] = og_street['content']

    return result


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
    Query search engines (DDGS) to:
    1. Automatically discover the official restaurant website
    2. Extract phone numbers and emails directly from snippets
    3. Discover official Facebook, Instagram, and LinkedIn profiles
    4. Return raw snippet text for downstream AI extraction
    """
    result = {
        'discovered_url': None,
        'phones': set(),
        'emails': set(),
        'social': {'facebook': set(), 'instagram': set(), 'linkedin': set(), 'twitter': set()},
        'snippet_text': ''
    }

    query = f"{name} {location}"
    collected_snippets = []

    if DDGS:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=6))
                for r in results:
                    href = r.get('href', '').strip()
                    title = r.get('title', '')
                    body = r.get('body', '')

                    snippet_entry = f"{title}: {body}"
                    collected_snippets.append(snippet_entry)

                    # Extract phones & emails directly from snippet text
                    result['phones'].update(extract_phones_from_text(snippet_entry))
                    result['emails'].update(extract_emails_from_text(snippet_entry))

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

    result['snippet_text'] = "\n".join(collected_snippets)
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
