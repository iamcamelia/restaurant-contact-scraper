"""
Core Scraper Engine
Coordinates HTTP requests, automatic website discovery, Schema.org structured data,
subpage traversal, social bio scraping, search enrichment, and Gemini AI validation.
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
    extract_structured_data,
    find_subpage_links,
    clean_phone,
    clean_email,
    scrape_social_profile,
    search_restaurant_online
)
from .ai import extract_contacts_with_ai, get_gemini_api_key

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

    def __init__(self, timeout: int = 12, max_subpages: int = 4, headers: Optional[Dict[str, str]] = None, gemini_api_key: Optional[str] = None):
        self.timeout = timeout
        self.max_subpages = max_subpages
        self.headers = headers or DEFAULT_HEADERS
        self.gemini_api_key = gemini_api_key or get_gemini_api_key()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_single_page(self, url: str) -> Dict:
        """Scrape raw content, Schema.org JSON-LD, tel:/mailto: links, and text from a single URL."""
        result = {
            'phones': set(),
            'emails': set(),
            'address': '',
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

            # 1. Parse Schema.org JSON-LD & meta tags
            struct = extract_structured_data(soup)
            result['phones'].update(struct['phones'])
            result['emails'].update(struct['emails'])
            result['address'] = struct['address']
            for k, v in struct['social'].items():
                result['social'][k].update(v)

            # 2. Parse direct href attributes (mailto: and tel:)
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.lower().startswith('mailto:'):
                    clean_target = href[7:]
                    for part in clean_target.split(','):
                        email = clean_email(part)
                        if email:
                            result['emails'].add(email)
                elif href.lower().startswith('tel:'):
                    phone = clean_phone(href)
                    if phone:
                        result['phones'].add(phone)

            # 3. Extract phone numbers and emails from raw page text
            result['phones'].update(extract_phones_from_text(text))
            result['emails'].update(extract_emails_from_text(text))

            # 4. Extract social media handles
            social = extract_social_links(soup, url)
            for k, v in social.items():
                result['social'][k].update(v)

            # 5. Identify internal subpages (Contact, About, Locations)
            result['subpages'] = find_subpage_links(soup, url, max_links=self.max_subpages)

        except Exception:
            pass

        return result

    def scrape_restaurant(
        self,
        name: str,
        url: str = "",
        location: str = "Houston, TX",
        check_subpages: bool = True,
        use_search: bool = True,
        use_ai: bool = True,
        custom_gemini_key: Optional[str] = None
    ) -> Dict:
        """
        Comprehensive multi-source contact extraction:
        1. Search Engine Auto-Discovery (DuckDuckGo / DDGS)
        2. Schema.org JSON-LD & Webpage Scraping
        3. Subpage Traversal (/locations, /contact, /about)
        4. Social Profile Deep Inspection (Facebook/Instagram about & bios)
        5. Gemini AI Verification & Extraction Layer
        """
        combined = {
            'name': name,
            'url': url.strip() if url else "",
            'address': '',
            'phones': set(),
            'emails': set(),
            'facebook': set(),
            'instagram': set(),
            'linkedin': set(),
            'twitter': set(),
            'sources': [],
            'branch_matches': [],
            'accumulated_text': '',
            'search_snippets': '',
            'ai_confidence': 'standard',
            'ai_notes': ''
        }

        # Step 1: Automatic Discovery if URL is empty or to enrich search
        if not combined['url'] or use_search:
            search_res = search_restaurant_online(name, location=location, session=self.session, timeout=self.timeout)
            combined['search_snippets'] = search_res.get('snippet_text', '')

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
            if home_data['address']:
                combined['address'] = home_data['address']
            for k in ['facebook', 'instagram', 'linkedin', 'twitter']:
                combined[k].update(home_data['social'][k])

            combined['accumulated_text'] += home_data.get('raw_text', '')[:3000]

            if home_data['phones'] or home_data['emails']:
                combined['sources'].append('Website')

            # Check subpages (Locations, Contact, About)
            if check_subpages and home_data['subpages']:
                for sub_url in home_data['subpages']:
                    sub_data = self.scrape_single_page(sub_url)
                    combined['phones'].update(sub_data['phones'])
                    combined['emails'].update(sub_data['emails'])
                    if sub_data['address'] and not combined['address']:
                        combined['address'] = sub_data['address']
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

        # Step 4: AI Extraction & Validation Layer (Gemini AI)
        active_gemini_key = custom_gemini_key or self.gemini_api_key
        if use_ai and active_gemini_key:
            ai_data = extract_contacts_with_ai(
                name=name,
                location=location,
                website_text=combined['accumulated_text'],
                search_snippets=combined['search_snippets'],
                api_key=active_gemini_key,
                timeout=self.timeout
            )
            if ai_data:
                combined['sources'].append('Gemini AI')
                combined['ai_confidence'] = ai_data.get('confidence', 'high')
                combined['ai_notes'] = ai_data.get('notes', '')

                if ai_data.get('phone'):
                    cleaned_ai_phone = clean_phone(ai_data['phone'])
                    if cleaned_ai_phone:
                        combined['phones'].add(cleaned_ai_phone)
                        # Prioritize AI validated phone
                        combined['branch_matches'].insert(0, cleaned_ai_phone)

                if ai_data.get('email'):
                    cleaned_ai_email = clean_email(ai_data['email'])
                    if cleaned_ai_email:
                        combined['emails'].add(cleaned_ai_email)

                if ai_data.get('address') and not combined['address']:
                    combined['address'] = ai_data['address']

                if ai_data.get('facebook') and not combined['facebook']:
                    fb_val = ai_data['facebook']
                    if 'facebook.com' not in fb_val:
                        fb_val = f"https://www.facebook.com/{fb_val.lstrip('@')}"
                    combined['facebook'].add(fb_val)

                if ai_data.get('instagram') and not combined['instagram']:
                    ig_val = ai_data['instagram']
                    if 'instagram.com' not in ig_val:
                        ig_val = f"https://www.instagram.com/{ig_val.lstrip('@')}"
                    combined['instagram'].add(ig_val)

        # Step 5: Primary Phone Selection (with Area Code & Branch Proximity Prioritization)
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
            best_phone = candidate_phones[0]
            for p in candidate_phones:
                digits_only = re.sub(r'\D', '', p)
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
            'address': combined['address'],
            'primary_phone': primary_phone,
            'primary_email': primary_email,
            'phone': ', '.join(sorted(combined['phones'])),
            'email': ', '.join(sorted(combined['emails'])),
            'facebook': ', '.join(sorted(combined['facebook'])),
            'instagram': ', '.join(sorted(combined['instagram'])),
            'linkedin': ', '.join(sorted(combined['linkedin'])),
            'twitter': ', '.join(sorted(combined['twitter'])),
            'sources': ', '.join(dict.fromkeys(combined['sources'])) if combined['sources'] else 'None',
            'ai_confidence': combined['ai_confidence'],
            'ai_notes': combined['ai_notes']
        }

    def scrape_batch(self, items: List[Dict], max_workers: int = 5, use_ai: bool = True, custom_gemini_key: Optional[str] = None, on_progress: Optional[Callable[[Dict, int, int], None]] = None) -> List[Dict]:
        """Batch scrape a list of restaurants concurrently with progress reporting."""
        results = []
        total = len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(
                    self.scrape_restaurant,
                    item['name'],
                    item.get('url', ''),
                    item.get('location', 'Houston, TX'),
                    True,
                    True,
                    use_ai,
                    custom_gemini_key
                ): item
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
                        'address': '',
                        'primary_phone': '',
                        'primary_email': '',
                        'phone': '',
                        'email': '',
                        'facebook': '',
                        'instagram': '',
                        'linkedin': '',
                        'twitter': '',
                        'sources': 'Error',
                        'ai_confidence': 'none',
                        'ai_notes': str(e),
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
