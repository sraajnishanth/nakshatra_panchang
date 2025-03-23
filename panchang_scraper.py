import json
import sys
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def safe_text(element):
    """Return the stripped text of an element, or an empty string if the element is None."""
    return element.get_text(strip=True) if element else ''

def parse_primary_header(soup):
    """Extracts date and location from the primary header."""
    header_data = {}
    header = soup.find('div', class_='panchang-box-primary-header')
    if header:
        date_elem = header.find('a', class_='t-lg b d-block')
        loc_elem = header.find('a', attrs={'data-focus': 'location'})
        header_data['date'] = safe_text(date_elem)
        header_data['location'] = safe_text(loc_elem)
    return header_data

def parse_secondary_header(soup):
    """Extracts secondary header details like Sunrise, Sunset, etc."""
    secondary = {}
    header = soup.find('div', class_='panchang-box-secondary-header')
    if header:
        items = header.find_all('div', class_='list-item-outer')
        for item in items:
            label_elem = item.find('span', class_='d-block t-sm')
            value_elem = item.find('span', class_='d-block b')
            label = safe_text(label_elem)
            value = safe_text(value_elem)
            if label:
                secondary[label] = value
    return secondary

def parse_data_blocks(soup):
    """
    Extracts detailed Panchang data.
    For blocks related to auspicious or inauspicious periods,
    each item is annotated with an "auspicious" flag.
    """
    details = {}
    details_section = soup.find('div', class_='panchang-box-details')
    if details_section:
        blocks = details_section.find_all('div', class_='panchang-box-data-block')
        for block in blocks:
            title_elem = block.find('span', class_='d-block b')
            if title_elem:
                title = safe_text(title_elem)
                block_classes = block.get("class", [])
                is_inauspicious = any("inauspicious" in cls for cls in block_classes)
                is_auspicious = any("auspicious" in cls for cls in block_classes) and not is_inauspicious
                items = []
                for li in block.find_all('li'):
                    text = " ".join(li.stripped_strings)
                    if ' - ' in text:
                        key, value = text.split(' - ', 1)
                        item = {
                            "name": key.strip(),
                            "time": value.strip()
                        }
                    else:
                        item = {"text": text}
                    if "Period" in title:
                        if is_inauspicious:
                            item["auspicious"] = False
                        elif is_auspicious:
                            item["auspicious"] = True
                        else:
                            item["auspicious"] = None
                    items.append(item)
                details[title] = items
    return details

def parse_gowri_panchang(soup):
    """
    Extracts Gowri Panchangam details from day and night tabs.
    Uses the row's class to include an extra "status" field indicating auspiciousness.
    """
    gowri = {}
    gowri_div = soup.find('div', id='gowri-panchang')
    if gowri_div:
        tab_panes = gowri_div.find_all('div', class_='tab-pane')
        for pane in tab_panes:
            tab_id = pane.get('id')
            if tab_id:
                entries = []
                rows = pane.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        period = safe_text(th)
                        time_val = safe_text(td)
                        row_classes = row.get("class", [])
                        if any("inauspicious" in cls for cls in row_classes):
                            status = "inauspicious"
                        elif any("auspicious" in cls for cls in row_classes):
                            status = "auspicious"
                        else:
                            status = None
                        entries.append({
                            'period': period,
                            'time': time_val,
                            'status': status
                        })
                gowri[tab_id] = entries
    return gowri

def parse_additional_tabs(soup):
    """
    Extracts content from additional tab sections (like Chandrabalam and Tarabalam).
    Stores all paragraph texts in a list under the tab's ID.
    """
    tabs_data = {}
    tabs_container = soup.find('div', class_='tab-content p-2 no-margin')
    if tabs_container:
        tab_panes = tabs_container.find_all('div', class_='tab-pane')
        for pane in tab_panes:
            tab_id = pane.get('id')
            if tab_id:
                paragraphs = [safe_text(p) for p in pane.find_all('p') if safe_text(p)]
                tabs_data[tab_id] = paragraphs
    return tabs_data

def scrape_panchang(html_content):
    """Parse all sections from HTML content and return a structured dictionary."""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        'primary_header': parse_primary_header(soup),
        'secondary_header': parse_secondary_header(soup),
        'details': parse_data_blocks(soup),
        'gowri_panchang': parse_gowri_panchang(soup),
        'additional_tabs': parse_additional_tabs(soup)
    }
    return data

def scrape_panchang_from_url(url):
    """Fetch the page content from the URL and scrape Panchang details."""
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return {}
    html_content = response.text
    return scrape_panchang(html_content)

def generate_url_for_date(date_obj):
    """Generates a Panchang URL for a given date object."""
    # Format date as YYYY-month-day with month in lower-case.
    date_str = date_obj.strftime("%Y-%B-%d").lower()
    return f"https://www.prokerala.com/astrology/tamil-panchangam/{date_str}.html"

def scrape_multiple_days(num_days=5):
    """Scrapes Panchang details for the given number of consecutive days starting from the current date."""
    start_date = datetime.today().date()
    all_data = {}
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        url = generate_url_for_date(current_date)
        print(f"Scraping {url} ...")
        data = scrape_panchang_from_url(url)
        all_data[current_date.isoformat()] = data
    return all_data

if __name__ == '__main__':
    try:
        num_days = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    except ValueError:
        num_days = 5

    results = scrape_multiple_days(num_days)
    print(json.dumps(results, indent=4, ensure_ascii=False))
