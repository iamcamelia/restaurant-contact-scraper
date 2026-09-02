"""
Core Scraper Engine
Coordinates HTTP requests, parses responses, traverses subpages, and aggregates contact info.
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
    clean_email
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
    """High-performance scraper for discovering restaurant contact information."""

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

    def scrape_restaurant(self, name: str, url: str, check_subpages: bool = True) -> Dict:
        """Comprehensive scrape for a restaurant: main page + contact subpages."""
        combined = {
            'name': name,
            'url': url,
            'phones': set(),
            'emails': set(),
            'facebook': set(),
            'instagram': set(),
            'linkedin': set(),
            'twitter': set(),
        }

        # Step 1: Scrape home page
        home_data = self.scrape_single_page(url)
        combined['phones'].update(home_data['phones'])
        combined['emails'].update(home_data['emails'])
        for k in combined['facebook'], combined['instagram'], combined['linkedin'], combined['twitter']:
            pass
        for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
            combined[k].update(home_data['social'][k])

        # Step 2: Scrape Contact / About subpages if needed
        if check_subpages and home_data['subpages']:
            for sub_url in home_data['subpages']:
                sub_data = self.scrape_single_page(sub_url)
                combined['phones'].update(sub_data['phones'])
                combined['emails'].update(sub_data['emails'])
                for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                    combined[k].update(sub_data['social'][k])
                time.sleep(0.2)

        return {
            'name': name,
            'url': url,
            'phone': ', '.join(sorted(combined['phones'])),
            'email': ', '.join(sorted(combined['emails'])),
            'facebook': ', '.join(sorted(combined['facebook'])),
            'instagram': ', '.join(sorted(combined['instagram'])),
            'linkedin': ', '.join(sorted(combined['linkedin'])),
            'twitter': ', '.join(sorted(combined['twitter'])),
        }

    def scrape_batch(self, items: List[Dict], max_workers: int = 5, on_progress: Optional[Callable[[Dict, int, int], None]] = None) -> List[Dict]:
        """Batch scrape a list of restaurants concurrently with progress reporting."""
        results = []
        total = len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self.scrape_restaurant, item['name'], item['url']): item
                for item in items
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed += 1
                try:
                    res = future.result()
                    # Preserve any metadata (e.g. original row number)
                    if 'row' in item:
                        res['row'] = item['row']
                    results.append(res)
                except Exception as e:
                    failed_res = {
                        'name': item.get('name', ''),
                        'url': item.get('url', ''),
                        'phone': '',
                        'email': '',
                        'facebook': '',
                        'instagram': '',
                        'linkedin': '',
                        'twitter': '',
                        'error': str(e)
                    }
                    if 'row' in item:
                        failed_res['row'] = item['row']
                    results.append(failed_res)

                if on_progress:
                    on_progress(results[-1], completed, total)

        # Re-sort to preserve original ordering if 'row' was present
        if any('row' in r for r in results):
            results.sort(key=lambda x: x.get('row', 0))

        return results
