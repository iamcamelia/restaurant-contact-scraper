"""
Contact Information Extractors & Search Enrichment
Extracts and sanitizes phone numbers, email addresses, and social media handles from web pages and search engines.
"""

import base64
import re
import urllib.parse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

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
    
    # Must be between 10 and 15 digits
    if 10 <= len(digits) <= 15:
        # Ignore obvious repetitive invalid digits (e.g. 1111111111, 0000000000)
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
    email = email.split('?')[0]  # Remove query parameters like ?subject=
    
    # RFC 5322 compatible regex check
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
        
        # Facebook
        if 'facebook.com/' in href_lower and not any(x in href_lower for x in ['/sharer', '/share', '/dialog', '/tr?']):
            social['facebook'].add(href)
        # Instagram
        elif 'instagram.com/' in href_lower and not any(x in href_lower for x in ['/share', '/p/']):
            social['instagram'].add(href)
        # LinkedIn
        elif 'linkedin.com/' in href_lower and not any(x in href_lower for x in ['/share', '/sharing']):
            social['linkedin'].add(href)
        # Twitter / X
        elif ('twitter.com/' in href_lower or 'x.com/' in href_lower) and not any(x in href_lower for x in ['/intent', '/share']):
            social['twitter'].add(href)
            
    return social


def find_subpage_links(soup: BeautifulSoup, base_url: str, max_links: int = 3) -> list[str]:
    """Find internal links to relevant subpages (Contact, About, Location, Hours)."""
    subpage_keywords = ['contact', 'about', 'location', 'hours', 'find-us', 'reach-us', 'info']
    links = set()
    base_domain = urlparse(base_url).netloc
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        href_lower = href.lower()
        text_lower = a.get_text().lower().strip()
        
        # Check if URL or link text contains keywords
        if any(kw in href_lower for kw in subpage_keywords) or any(kw in text_lower for kw in subpage_keywords):
            full_url = urljoin(base_url, href)
            # Only follow links belonging to the exact same domain
            if urlparse(full_url).netloc == base_domain and full_url != base_url:
                links.add(full_url)
                if len(links) >= max_links:
                    break
                    
    return list(links)


def decode_bing_url(url: str) -> str:
    """Decode redirect URLs generated by Bing search results."""
    try:
        if 'bing.com/ck/a?' in url and 'u=' in url:
            parts = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            u_val = parts.get('u', [''])[0]
            if u_val.startswith('a1'):
                encoded = u_val[2:]
                # Add padding if needed
                padded = encoded + '=' * (-len(encoded) % 4)
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                return decoded
    except Exception:
        pass
    return url


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
                
            # Also check page body text
            page_text = soup.get_text(separator=' ')
            result['phones'].update(extract_phones_from_text(page_text))
            result['emails'].update(extract_emails_from_text(page_text))
    except Exception:
        pass
    return result


def search_enrichment(name: str, location: str = "Houston", session: requests.Session = None, timeout: int = 8) -> dict:
    """Search Bing to discover missing social media pages, phone numbers, and emails."""
    if session is None:
        session = requests.Session()
        
    result = {
        'phones': set(),
        'emails': set(),
        'social': {'facebook': set(), 'instagram': set(), 'linkedin': set(), 'twitter': set()}
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    
    queries = [
        f'site:facebook.com "{name}" {location}',
        f'site:instagram.com "{name}" {location}',
        f'"{name}" {location} restaurant phone email contact'
    ]
    
    for q in queries:
        try:
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
            resp = session.get(search_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Check snippets and titles for contact info
                for li in soup.select('li.b_algo'):
                    a = li.select_one('h2 a')
                    p = li.select_one('.b_caption')
                    
                    if a and a.get('href'):
                        dest_url = decode_bing_url(a['href'])
                        dest_lower = dest_url.lower()
                        if 'facebook.com/' in dest_lower and not any(x in dest_lower for x in ['/sharer', '/share', '/dialog']):
                            result['social']['facebook'].add(dest_url)
                        elif 'instagram.com/' in dest_lower and '/p/' not in dest_lower:
                            result['social']['instagram'].add(dest_url)
                        elif 'linkedin.com/' in dest_lower and '/share' not in dest_lower:
                            result['social']['linkedin'].add(dest_url)
                            
                    if p:
                        snippet_text = p.get_text()
                        result['phones'].update(extract_phones_from_text(snippet_text))
                        result['emails'].update(extract_emails_from_text(snippet_text))
        except Exception:
            pass
            
    return result
