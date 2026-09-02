"""
Contact Information Extractors
Extracts and sanitizes phone numbers, email addresses, and social media handles from web pages.
"""

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

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
