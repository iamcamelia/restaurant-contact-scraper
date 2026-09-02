"""
Core Scraper Engine
Coordinates HTTP requests, parses responses, traverses subpages, checks social profiles, and runs search enrichment.
"""

import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable
from .extractors import (
    extract_phones_from_text,
    extract_emails_from_text,
    extract_social_links,
    find_subpage_links,
    clean_phone,
    clean_email,
    scrape_social_profile,
    search_enrichment
)

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}


class RestaurantScraper:
    """High-performance multi-source scraper for discovering restaurant contact information."""

    def __init__(self, timeout: int = 12, max_subpages: int = 3, headers: Optional[Dict[str, str]] = None):
        self.timeout = timeout
        self.max_subpages = max_subpages
        self.headers = headers or DEFAULT_HEADERS
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_single_page(self, url: str) -> Dict:
        """Scrape raw content, tel:/mailto: links, and text from a single URL."""
        result = {
            'phones': set(),
            'emails': set(),
            'social': {'facebook': set(), 'instagram': set(), 'linkedin': set(), 'twitter': set()},
            'subpages': []
        }

        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code >= 400:
                return result

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator=' ')

            # 1. Parse direct href attributes (mailto: and tel:)
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.lower().startswith('mailto:'):
                    email = clean_email(href)
                    if email:
                        result['emails'].add(email)
                elif href.lower().startswith('tel:'):
                    phone = clean_phone(href)
                    if phone:
                        result['phones'].add(phone)

            # 2. Extract phone numbers and emails from raw page text
            result['phones'].update(extract_phones_from_text(text))
            result['emails'].update(extract_emails_from_text(text))

            # 3. Extract social media handles
            social = extract_social_links(soup, url)
            for k, v in social.items():
                result['social'][k].update(v)

            # 4. Identify internal subpages (Contact, About, Locations)
            result['subpages'] = find_subpage_links(soup, url, max_links=self.max_subpages)

        except Exception:
            pass

        return result

    def scrape_restaurant(self, name: str, url: str, location: str = "Houston, TX", check_subpages: bool = True, use_search: bool = True) -> Dict:
        """
        Comprehensive scrape:
        1. Official Website (home page)
        2. Subpages (Contact Us, About Us, Locations)
        3. Social Profiles (Facebook / Instagram public bio & description)
        4. Search Enrichment (Bing / DuckDuckGo search queries for phone/email/socials)
        """
        combined = {
            'name': name,
            'url': url,
            'phones': set(),
            'emails': set(),
            'facebook': set(),
            'instagram': set(),
            'linkedin': set(),
            'twitter': set(),
            'sources': []
        }

        # Step 1: Scrape official website
        if url and url.strip():
            home_data = self.scrape_single_page(url)
            combined['phones'].update(home_data['phones'])
            combined['emails'].update(home_data['emails'])
            for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                combined[k].update(home_data['social'][k])

            if home_data['phones'] or home_data['emails']:
                combined['sources'].append('Official Website')

            # Step 2: Scrape Contact / About subpages
            if check_subpages and home_data['subpages']:
                for sub_url in home_data['subpages']:
                    sub_data = self.scrape_single_page(sub_url)
                    combined['phones'].update(sub_data['phones'])
                    combined['emails'].update(sub_data['emails'])
                    for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                        combined[k].update(sub_data['social'][k])
                    time.sleep(0.15)
                if len(home_data['subpages']) > 0:
                    combined['sources'].append(f'Subpages ({len(home_data["subpages"])} checked)')

        # Step 3: Search Engine Enrichment (if missing email or phone, or to find missing socials)
        if use_search and (not combined['phones'] or not combined['emails'] or not combined['facebook']):
            search_res = search_enrichment(name, location=location, session=self.session, timeout=self.timeout)
            new_phones = search_res['phones'] - combined['phones']
            new_emails = search_res['emails'] - combined['emails']
            if new_phones or new_emails:
                combined['phones'].update(new_phones)
                combined['emails'].update(new_emails)
                combined['sources'].append('Search Snippets')

            for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                combined[k].update(search_res['social'][k])

        # Step 4: Check Facebook / Instagram profiles for direct contact info
        social_contacts_found = False
        for fb_url in list(combined['facebook'])[:1]:
            fb_res = scrape_social_profile(fb_url, session=self.session, timeout=self.timeout)
            if fb_res['phones'] or fb_res['emails']:
                combined['phones'].update(fb_res['phones'])
                combined['emails'].update(fb_res['emails'])
                social_contacts_found = True

        for ig_url in list(combined['instagram'])[:1]:
            ig_res = scrape_social_profile(ig_url, session=self.session, timeout=self.timeout)
            if ig_res['phones'] or ig_res['emails']:
                combined['phones'].update(ig_res['phones'])
                combined['emails'].update(ig_res['emails'])
                social_contacts_found = True

        if social_contacts_found:
            combined['sources'].append('Social Profiles (FB/IG)')

        # Best primary phone & email
        primary_phone = sorted(list(combined['phones']))[0] if combined['phones'] else ''
        primary_email = sorted(list(combined['emails']))[0] if combined['emails'] else ''

        return {
            'name': name,
            'url': url,
            'primary_phone': primary_phone,
            'primary_email': primary_email,
            'phone': ', '.join(sorted(combined['phones'])),
            'email': ', '.join(sorted(combined['emails'])),
            'facebook': ', '.join(sorted(combined['facebook'])),
            'instagram': ', '.join(sorted(combined['instagram'])),
            'linkedin': ', '.join(sorted(combined['linkedin'])),
            'twitter': ', '.join(sorted(combined['twitter'])),
            'sources': ', '.join(combined['sources']) if combined['sources'] else 'None'
        }

    def scrape_batch(self, items: List[Dict], max_workers: int = 5, on_progress: Optional[Callable[[Dict, int, int], None]] = None) -> List[Dict]:
        """Batch scrape a list of restaurants concurrently with progress reporting."""
        results = []
        total = len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self.scrape_restaurant, item['name'], item.get('url', ''), item.get('location', 'Houston, TX')): item
                for item in items
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed += 1
                try:
                    res = future.result()
                    if 'row' in item:
                        res['row'] = item['row']
                    results.append(res)
                except Exception as e:
                    failed_res = {
                        'name': item.get('name', ''),
                        'url': item.get('url', ''),
                        'primary_phone': '',
                        'primary_email': '',
                        'phone': '',
                        'email': '',
                        'facebook': '',
                        'instagram': '',
                        'linkedin': '',
                        'twitter': '',
                        'sources': 'Error',
                        'error': str(e)
                    }
                    if 'row' in item:
                        failed_res['row'] = item['row']
                    results.append(failed_res)

                if on_progress:
                    on_progress(results[-1], completed, total)

        if any('row' in r for r in results):
            results.sort(key=lambda x: x.get('row', 0))

        return results
