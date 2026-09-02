"""
Core Scraper Engine
Coordinates HTTP requests, automatic website discovery, subpage traversal, social bio scraping, and search enrichment.
"""

import time
import re
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
    search_restaurant_online
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

    def __init__(self, timeout: int = 12, max_subpages: int = 4, headers: Optional[Dict[str, str]] = None):
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
            'subpages': [],
            'raw_text': ''
        }

        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code >= 400:
                return result

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator=' ')
            result['raw_text'] = text

            # 1. Parse direct href attributes (mailto: and tel:)
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.lower().startswith('mailto:'):
                    # mailto: can contain multiple comma-separated emails
                    clean_target = href[7:]
                    for part in clean_target.split(','):
                        email = clean_email(part)
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

    def scrape_restaurant(self, name: str, url: str = "", location: str = "Houston, TX", check_subpages: bool = True, use_search: bool = True) -> Dict:
        """
        Comprehensive multi-source contact extraction:
        1. Search Engine Auto-Discovery (if URL is empty or to find socials/contacts)
        2. Official Website Scraping (homepage + subpages)
        3. Social Profile Deep Inspection (Facebook/Instagram about & bios)
        """
        combined = {
            'name': name,
            'url': url.strip() if url else "",
            'phones': set(),
            'emails': set(),
            'facebook': set(),
            'instagram': set(),
            'linkedin': set(),
            'twitter': set(),
            'sources': [],
            'branch_matches': []
        }

        # Step 1: Automatic Discovery if URL is empty or to enrich search
        if not combined['url'] or use_search:
            search_res = search_restaurant_online(name, location=location, session=self.session, timeout=self.timeout)
            
            # If no URL was provided by user, use the auto-discovered website!
            if not combined['url'] and search_res['discovered_url']:
                combined['url'] = search_res['discovered_url']
                combined['sources'].append('Auto-Discovered Website')

            combined['phones'].update(search_res['phones'])
            combined['emails'].update(search_res['emails'])
            for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                combined[k].update(search_res['social'][k])

            if search_res['phones'] or search_res['emails']:
                combined['sources'].append('Search Results')

        # Step 2: Scrape Official Website (Homepage & Subpages)
        if combined['url']:
            home_data = self.scrape_single_page(combined['url'])
            combined['phones'].update(home_data['phones'])
            combined['emails'].update(home_data['emails'])
            for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                combined[k].update(home_data['social'][k])

            if home_data['phones'] or home_data['emails']:
                combined['sources'].append('Website')

            # Check subpages (Locations, Contact, About)
            if check_subpages and home_data['subpages']:
                for sub_url in home_data['subpages']:
                    sub_data = self.scrape_single_page(sub_url)
                    combined['phones'].update(sub_data['phones'])
                    combined['emails'].update(sub_data['emails'])
                    for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                        combined[k].update(sub_data['social'][k])

                    # Proximity matching: phones near branch keywords (e.g. 6th, burnet, downtown)
                    for kw in name.lower().split():
                        if len(kw) >= 3 and kw in ['6th', 'sixth', 'burnet', 'heights', 'downtown', 'midtown', 'west', 'east']:
                            pattern = re.compile(re.escape(kw), re.IGNORECASE)
                            for m in pattern.finditer(sub_data['raw_text']):
                                snippet = sub_data['raw_text'][max(0, m.start() - 120):min(len(sub_data['raw_text']), m.end() + 120)]
                                nearby = extract_phones_from_text(snippet)
                                if nearby:
                                    combined['branch_matches'].extend(nearby)

                    time.sleep(0.15)
                combined['sources'].append('Subpages')

        # Step 3: Deep inspect Facebook / Instagram profiles
        social_found = False
        for fb_url in list(combined['facebook'])[:1]:
            fb_res = scrape_social_profile(fb_url, session=self.session, timeout=self.timeout)
            if fb_res['phones'] or fb_res['emails']:
                combined['phones'].update(fb_res['phones'])
                combined['emails'].update(fb_res['emails'])
                social_found = True

        for ig_url in list(combined['instagram'])[:1]:
            ig_res = scrape_social_profile(ig_url, session=self.session, timeout=self.timeout)
            if ig_res['phones'] or ig_res['emails']:
                combined['phones'].update(ig_res['phones'])
                combined['emails'].update(ig_res['emails'])
                social_found = True

        if social_found:
            combined['sources'].append('Social Profiles')

        # Primary Phone Selection (with Area Code & Branch Proximity Prioritization)
        city_area_codes = {
            'austin': ['512', '737'],
            'houston': ['713', '281', '832', '346'],
            'dallas': ['214', '972', '469'],
            'san antonio': ['210', '726'],
            'fort worth': ['817', '682']
        }
        preferred_codes = []
        for city, codes in city_area_codes.items():
            if city in location.lower() or city in name.lower():
                preferred_codes.extend(codes)

        candidate_phones = list(combined['branch_matches']) + sorted(list(combined['phones']))
        primary_phone = ''
        if candidate_phones:
            # Score phones: boost if matches city area code, boost if branch proximity match
            best_phone = candidate_phones[0]
            for p in candidate_phones:
                digits_only = re.sub(r'\D', '', p)
                # Strip leading 1 if 11 digits
                clean_digits = digits_only[1:] if len(digits_only) == 11 and digits_only.startswith('1') else digits_only
                if preferred_codes and any(clean_digits.startswith(code) for code in preferred_codes):
                    best_phone = p
                    break
            primary_phone = best_phone

        # Primary Email Selection (prioritize @domain emails over generic ones)
        primary_email = ''
        if combined['emails']:
            sorted_emails = sorted(list(combined['emails']))
            domain_match = None
            if combined['url']:
                netloc = requests.utils.urlparse(combined['url']).netloc.replace('www.', '')
                for e in sorted_emails:
                    if netloc in e:
                        domain_match = e
                        break
            primary_email = domain_match or sorted_emails[0]

        return {
            'name': name,
            'url': combined['url'],
            'primary_phone': primary_phone,
            'primary_email': primary_email,
            'phone': ', '.join(sorted(combined['phones'])),
            'email': ', '.join(sorted(combined['emails'])),
            'facebook': ', '.join(sorted(combined['facebook'])),
            'instagram': ', '.join(sorted(combined['instagram'])),
            'linkedin': ', '.join(sorted(combined['linkedin'])),
            'twitter': ', '.join(sorted(combined['twitter'])),
            'sources': ', '.join(dict.fromkeys(combined['sources'])) if combined['sources'] else 'None'
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
