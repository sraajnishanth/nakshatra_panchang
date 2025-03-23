import re
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from collections import defaultdict

# ---------------- Tharai Chart Configurations ----------------
# Poorattathi Tharai Chart (Example: original chart)
THARAI_CHART_POORATTATHI = [
    {
        "tharai": "Birth Tharai",
        "nakshatra_numbers": [1, 10, 19],
        "nakshatra_names": ["Poorattathi", "Punarpoosam", "Vishakam"],
        "auspicious": True
    },
    {
        "tharai": "Wealth Tharai",
        "nakshatra_numbers": [2, 11, 20],
        "nakshatra_names": ["Uthirattathi", "Poosam", "Anusham"],
        "auspicious": True
    },
    {
        "tharai": "Accident Tharai",
        "nakshatra_numbers": [3, 12, 21],
        "nakshatra_names": ["Revathi", "Ayilyam", "Kettai"],
        "auspicious": False
    },
    {
        "tharai": "Safety Tharai",
        "nakshatra_numbers": [4, 13, 22],
        "nakshatra_names": ["Aswini", "Magam", "Moolam"],
        "auspicious": True
    },
    {
        "tharai": "Obstacle Tharai",
        "nakshatra_numbers": [5, 14, 23],
        "nakshatra_names": ["Parani", "Pooram", "Pooradam"],
        "auspicious": False
    },
    {
        "tharai": "Success Tharai",
        "nakshatra_numbers": [6, 15, 24],
        "nakshatra_names": ["Karthikai", "Uthiram", "Uthiradam"],
        "auspicious": True
    },
    {
        "tharai": "Struggle Tharai",
        "nakshatra_numbers": [7, 16, 25],
        "nakshatra_names": ["Rohini", "Astham", "Thiruvonam"],
        "auspicious": False
    },
    {
        "tharai": "Friendship Tharai",
        "nakshatra_numbers": [8, 17, 26],
        "nakshatra_names": ["Mirugaseeridam", "Chithirai", "Avittam"],
        "auspicious": True
    },
    {
        "tharai": "Best Friend Tharai",
        "nakshatra_numbers": [9, 18, 27],
        "nakshatra_names": ["Thiruvadhirai", "Swathi", "Sadhayam"],
        "auspicious": True
    }
]


# Rohini Tharai Chart (Example from the provided table; all names are translated to English)
THARAI_CHART_ROHINI = [
    {
        "tharai": "Birth Tharai",
        "nakshatra_numbers": [1, 10, 19],
        "nakshatra_names": ["Rohini", "Astham", "Thiruvonam"],
        "auspicious": True
    },
    {
        "tharai": "Wealth Tharai",
        "nakshatra_numbers": [2, 11, 20],
        "nakshatra_names": ["Mirugaseeridam", "Chithirai", "Avittam"],
        "auspicious": True
    },
    {
        "tharai": "Accident Tharai",
        "nakshatra_numbers": [3, 12, 21],
        "nakshatra_names": ["Thiruvadhirai", "Swathi", "Sadhayam"],
        "auspicious": False
    },
    {
        "tharai": "Safety Tharai",
        "nakshatra_numbers": [4, 13, 22],
        "nakshatra_names": ["Punarpoosam", "Vishakam", "Poorattathi"],
        "auspicious": True
    },
    {
        "tharai": "Obstacle Tharai",
        "nakshatra_numbers": [5, 14, 23],
        "nakshatra_names": ["Poosam", "Anusham", "Uthirattathi"],
        "auspicious": False
    },
    {
        "tharai": "Success Tharai",
        "nakshatra_numbers": [6, 15, 24],
        "nakshatra_names": ["Ayilyam", "Kettai", "Revathi"],
        "auspicious": True
    },
    {
        "tharai": "Struggle Tharai",
        "nakshatra_numbers": [7, 16, 25],
        "nakshatra_names": ["Aswini", "Magam", "Moolam"],
        "auspicious": False
    },
    {
        "tharai": "Friendship Tharai",
        "nakshatra_numbers": [8, 17, 26],
        "nakshatra_names": ["Parani", "Pooram", "Pooradam"],
        "auspicious": True
    },
    {
        "tharai": "Best Friend Tharai",
        "nakshatra_numbers": [9, 18, 27],
        "nakshatra_names": ["Karthikai", "Uthiram", "Uthiradam"],
        "auspicious": True
    }
]

THARAI_CHART_BHARANI = [
    {
        "tharai": "Birth Tharai",
        "nakshatra_numbers": [1, 10, 19],
        "nakshatra_names": ["Bharani", "Pooram", "Pooradam"],
        "auspicious": True
    },
    {
        "tharai": "Wealth Tharai",
        "nakshatra_numbers": [2, 11, 20],
        "nakshatra_names": ["Karthikai", "Uthiram", "Uthiradam"],
        "auspicious": True
    },
    {
        "tharai": "Accident Tharai",
        "nakshatra_numbers": [3, 12, 21],
        "nakshatra_names": ["Rohini", "Astham", "Thiruvonam"],
        "auspicious": False
    },
    {
        "tharai": "Safety Tharai",
        "nakshatra_numbers": [4, 13, 22],
        "nakshatra_names": ["Mirugaseeridam", "Chithirai", "Avittam"],
        "auspicious": True
    },
    {
        "tharai": "Obstacle Tharai",
        "nakshatra_numbers": [5, 14, 23],
        "nakshatra_names": ["Thiruvadhirai", "Swathi", "Sadhayam"],
        "auspicious": False
    },
    {
        "tharai": "Success Tharai",
        "nakshatra_numbers": [6, 15, 24],
        "nakshatra_names": ["Punarpoosam", "Vishakam", "Poorattathi"],
        "auspicious": True
    },
    {
        "tharai": "Struggle Tharai",
        "nakshatra_numbers": [7, 16, 25],
        "nakshatra_names": ["Poosam", "Anusham", "Uthirattathi"],
        "auspicious": False
    },
    {
        "tharai": "Friendship Tharai",
        "nakshatra_numbers": [8, 17, 26],
        "nakshatra_names": ["Ayilyam", "Kettai", "Revathi"],
        "auspicious": True
    },
    {
        "tharai": "Best Friend Tharai",
        "nakshatra_numbers": [9, 18, 27],
        "nakshatra_names": ["Aswini", "Magam", "Moolam"],
        "auspicious": True
    }
]

THARAI_CHART_CHITHIRAI = [
    {
        "tharai": "Birth Tharai",
        "nakshatra_numbers": [1, 10, 19],
        "nakshatra_names": ["Chithirai", "Avittam", "Mirugaseeridam"],
        "auspicious": True
    },
    {
        "tharai": "Wealth Tharai",
        "nakshatra_numbers": [2, 11, 20],
        "nakshatra_names": ["Thiruvadhirai", "Swathi", "Sadhayam"],
        "auspicious": True
    },
    {
        "tharai": "Accident Tharai",
        "nakshatra_numbers": [3, 12, 21],
        "nakshatra_names": ["Punarpoosam", "Vishakam", "Poorattathi"],
        "auspicious": False
    },
    {
        "tharai": "Safety Tharai",
        "nakshatra_numbers": [4, 13, 22],
        "nakshatra_names": ["Poosam", "Anusham", "Uthirattathi"],
        "auspicious": True
    },
    {
        "tharai": "Obstacle Tharai",
        "nakshatra_numbers": [5, 14, 23],
        "nakshatra_names": ["Ayilyam", "Kettai", "Revathi"],
        "auspicious": False
    },
    {
        "tharai": "Success Tharai",
        "nakshatra_numbers": [6, 15, 24],
        "nakshatra_names": ["Aswini", "Magam", "Moolam"],
        "auspicious": True
    },
    {
        "tharai": "Struggle Tharai",
        "nakshatra_numbers": [7, 16, 25],
        "nakshatra_names": ["Parani", "Pooram", "Pooradam"],
        "auspicious": False
    },
    {
        "tharai": "Friendship Tharai",
        "nakshatra_numbers": [8, 17, 26],
        "nakshatra_names": ["Karthikai", "Uthiram", "Uthiradam"],
        "auspicious": True
    },
    {
        "tharai": "Best Friend Tharai",
        "nakshatra_numbers": [9, 18, 27],
        "nakshatra_names": ["Rohini", "Astham", "Thiruvonam"],
        "auspicious": True
    }
]


# Mapping of available tharai charts
THARAI_CHARTS = {
    "Poorattathi": THARAI_CHART_POORATTATHI,
    "Chithirai": THARAI_CHART_CHITHIRAI,
    "Rohini": THARAI_CHART_ROHINI,
    "Bharani": THARAI_CHART_BHARANI
}

# ------------------ Scraping & Parsing Code ------------------

def safe_text(element):
    return element.get_text(strip=True) if element else ''

def parse_primary_header(soup):
    header_data = {}
    header = soup.find('div', class_='panchang-box-primary-header')
    if header:
        date_elem = header.find('a', class_='t-lg b d-block')
        loc_elem = header.find('a', attrs={'data-focus': 'location'})
        header_data['date'] = safe_text(date_elem)
        header_data['location'] = safe_text(loc_elem)
    return header_data

def parse_secondary_header(soup):
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
                        item = {"name": key.strip(), "time": value.strip()}
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
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Error fetching URL {url}: {e}")
        return {}
    html_content = response.text
    return scrape_panchang(html_content)

def generate_url_for_date(date_obj):
    date_str = date_obj.strftime("%Y-%B-%d").lower()
    return f"https://www.prokerala.com/astrology/tamil-panchangam/{date_str}.html"

def scrape_multiple_days(num_days=5, start_date=None):
    if start_date is None:
        start_date = datetime.today().date()
    all_data = {}
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        url = generate_url_for_date(current_date)
        st.info(f"Scraping {url} ...")
        data = scrape_panchang_from_url(url)
        all_data[current_date.isoformat()] = data
    return all_data

# ------------------- Analysis Functions -------------------

def get_nakshatra_auspicious_info(scraped_data, tharai_chart):
    info_list = []
    for day, data in scraped_data.items():
        details = data.get("details", {})
        for key, items in details.items():
            if "nakshatram" in key.lower():
                for item in items:
                    if "name" in item and "time" in item:
                        nak_name = item["name"].strip().lower()
                        for tharai in tharai_chart:
                            for chart_nak in tharai["nakshatra_names"]:
                                if nak_name == chart_nak.lower():
                                    info_list.append({
                                        "date": day,
                                        "nakshatra": item["name"],
                                        "time": item["time"],
                                        "tharai": tharai["tharai"],
                                        "auspicious": tharai["auspicious"]
                                    })
                                    break
    return info_list

def get_time_periods(scraped_data):
    periods = []
    for day, data in scraped_data.items():
        details = data.get("details", {})
        for key, items in details.items():
            key_lower = key.lower()
            if "period" in key_lower:
                if "auspicious period" in key_lower and "inauspicious" not in key_lower:
                    period_type = "Auspicious"
                elif "inauspicious period" in key_lower:
                    period_type = "Inauspicious"
                else:
                    period_type = "Unknown"
                for item in items:
                    if "name" in item and "time" in item:
                        periods.append({
                            "date": day,
                            "period_type": period_type,
                            "period": item["name"],
                            "time": item["time"]
                        })
    return periods

def get_auspicious_dates_and_times(scraped_data, tharai_chart):
    nak_info = get_nakshatra_auspicious_info(scraped_data, tharai_chart)
    auspicious_nak = {}
    for rec in nak_info:
        if rec["auspicious"]:
            date = rec["date"]
            auspicious_nak.setdefault(date, []).append(f'{rec["nakshatra"]} ({rec["time"]})')
    
    time_periods_all = get_time_periods(scraped_data)
    ausp_times = {}
    for rec in time_periods_all:
        if rec["period_type"].lower() == "auspicious":
            date = rec["date"]
            ausp_times.setdefault(date, []).append(f'{rec["period"]}: {rec["time"]}')
    
    result = []
    all_dates = set(auspicious_nak.keys()).union(ausp_times.keys())
    for d in sorted(all_dates):
        result.append({
            "date": d,
            "auspicious_nakshatras": ", ".join(auspicious_nak.get(d, [])),
            "auspicious_periods": ", ".join(ausp_times.get(d, []))
        })
    return result

# Precise Intersection with Reasoning

def parse_datetime_str(date_str, fallback_year):
    pattern_year = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{4}'
    if not re.search(pattern_year, date_str):
        parts = date_str.split()
        if len(parts) >= 2:
            date_str = f"{parts[0]} {parts[1]} {fallback_year} {' '.join(parts[2:])}"
    fmt = "%b %d %Y %I:%M %p"
    return datetime.strptime(date_str, fmt)

def parse_nakshatra_interval(text_line, fallback_year):
    if " - " not in text_line or "–" not in text_line:
        return None
    nak_part, times_part = text_line.split(" - ", 1)
    if "–" not in times_part:
        return None
    start_str, end_str = times_part.split("–", 1)
    start_str = start_str.strip()
    end_str = end_str.strip()
    start_dt = parse_datetime_str(start_str, fallback_year)
    end_dt = parse_datetime_str(end_str, fallback_year)
    return nak_part.strip(), start_dt, end_dt

def parse_day_period_interval(day_str, item):
    if "name" not in item or "time" not in item:
        return None
    period_name = item["name"]
    time_str = item["time"]
    if "–" not in time_str:
        return None
    start_str, end_str = time_str.split("–", 1)
    start_str = start_str.strip()
    end_str = end_str.strip()
    day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
    fmt_time = "%I:%M %p"
    try:
        start_t = datetime.strptime(start_str, fmt_time).time()
        end_t = datetime.strptime(end_str, fmt_time).time()
    except ValueError:
        return None
    start_dt = datetime.combine(day_date, start_t)
    end_dt = datetime.combine(day_date, end_t)
    return period_name, start_dt, end_dt

def intersect_intervals(a_start, a_end, b_start, b_end):
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end > start:
        return (start, end)
    return None

def refine_auspicious_times(scraped_data, tharai_chart):
    nakshatra_intervals = []
    for day, day_data in scraped_data.items():
        fallback_year = day.split("-")[0]
        details = day_data.get("details", {})
        for title, items in details.items():
            if "nakshatram" in title.lower():
                for li in items:
                    if "name" in li and "time" in li:
                        text_line = f"{li['name']} - {li['time']}"
                        parsed = parse_nakshatra_interval(text_line, fallback_year)
                        if parsed:
                            nak_name, start_dt, end_dt = parsed
                            is_ausp = False
                            nak_lower = nak_name.lower()
                            for tharai in tharai_chart:
                                for chart_nak in tharai["nakshatra_names"]:
                                    if nak_lower == chart_nak.lower() and tharai["auspicious"]:
                                        is_ausp = True
                                        break
                                if is_ausp:
                                    break
                            nakshatra_intervals.append({
                                "day": day,
                                "nakshatra_name": nak_name,
                                "start": start_dt,
                                "end": end_dt,
                                "is_tharai_auspicious": is_ausp
                            })

    panchang_periods = []
    for day, day_data in scraped_data.items():
        details = day_data.get("details", {})
        for title, items in details.items():
            if "auspicious period" in title.lower() and "inauspicious" not in title.lower():
                for li in items:
                    parsed = parse_day_period_interval(day, li)
                    if parsed:
                        period_name, start_dt, end_dt = parsed
                        panchang_periods.append({
                            "day": day,
                            "period_name": period_name,
                            "start": start_dt,
                            "end": end_dt
                        })

    results = []
    nak_by_day = defaultdict(list)
    per_by_day = defaultdict(list)
    for nk in nakshatra_intervals:
        nak_by_day[nk["day"]].append(nk)
    for pp in panchang_periods:
        per_by_day[pp["day"]].append(pp)

    all_days = set(nak_by_day.keys()) | set(per_by_day.keys())
    for d in sorted(all_days):
        for nk in nak_by_day[d]:
            if not nk["is_tharai_auspicious"]:
                continue
            for pp in per_by_day[d]:
                overlap = intersect_intervals(nk["start"], nk["end"], pp["start"], pp["end"])
                if overlap:
                    s, e = overlap
                    reason_str = (
                        f"**Nakshatra** '{nk['nakshatra_name']}' is auspicious per selected Tharai Chart, "
                        f"and **Panchang Period** '{pp['period_name']}' is labeled auspicious."
                    )
                    results.append({
                        "date": d,
                        "nakshatra": nk["nakshatra_name"],
                        "nakshatra_interval": f"{nk['start']} – {nk['end']}",
                        "panchang_period": pp["period_name"],
                        "period_interval": f"{pp['start']} – {pp['end']}",
                        "overlap": f"{s} – {e}",
                        "reason": reason_str
                    })
    return results

# ------------------- Streamlit Dashboard -------------------

st.title("Panchang Dashboard with Custom Tharai Chart")
st.markdown("""
This dashboard scrapes Tamil Panchang details from Prokerala for multiple days.
You can select your nakshatra – and the calculations will be made against the corresponding Tharai Chart.
It displays:
- Full Panchang details by date
- Basic nakshatra and time period analysis
- **True Auspicious Intervals (Intersection)** with explanations (reason)
""")

# Allow user to select their nakshatra (chart)
selected_nakshatra = st.selectbox("Select your nakshatra", options=list(THARAI_CHARTS.keys()))
selected_chart = THARAI_CHARTS[selected_nakshatra]

# Date and days input
selected_date = st.date_input("Select start date", value=datetime.today().date())
num_days = st.number_input("Enter number of days to scrape", min_value=1, value=5, step=1)

if st.button("Scrape Panchang Data"):
    with st.spinner("Scraping Panchang details..."):
        scraped_results = scrape_multiple_days(num_days=num_days, start_date=selected_date)
    st.success("Scraping complete!")

    days = list(scraped_results.keys())
    if not days:
        st.warning("No data found.")
    else:
        tabs = st.tabs(days)
        for i, day in enumerate(days):
            with tabs[i]:
                st.subheader(f"Panchang for {day}")
                data_for_day = scraped_results[day]
                primary = data_for_day.get("primary_header", {})
                secondary = data_for_day.get("secondary_header", {})
                st.markdown("**Primary Details**")
                st.write(primary)
                st.markdown("**Secondary Details**")
                st.write(secondary)
                details = data_for_day.get("details", {})
                if details:
                    st.markdown("**Detailed Panchang Data**")
                    for title, items in details.items():
                        st.markdown(f"***{title}***")
                        st.write(items)
                gowri = data_for_day.get("gowri_panchang", {})
                if gowri:
                    st.markdown("**Gowri Panchangam**")
                    for tab_id, entries in gowri.items():
                        st.markdown(f"***{tab_id}***")
                        st.write(entries)
                additional = data_for_day.get("additional_tabs", {})
                if additional:
                    st.markdown("**Additional Information**")
                    for tab_id, paragraphs in additional.items():
                        st.markdown(f"***{tab_id}***")
                        for para in paragraphs:
                            st.write(para)
        
        # Basic Analysis (Old Approach)
        nak_info = get_nakshatra_auspicious_info(scraped_results, selected_chart)
        if nak_info:
            st.markdown("## Nakshatra Analysis (Basic)")
            df_nak = pd.DataFrame(nak_info)
            st.dataframe(df_nak)
        else:
            st.info("No nakshatra information found.")
        
        time_periods = get_time_periods(scraped_results)
        if time_periods:
            st.markdown("## Time Periods from Panchang (Basic)")
            df_time = pd.DataFrame(time_periods)
            st.dataframe(df_time)
        else:
            st.info("No period details found.")
        
        auspicious_summary = get_auspicious_dates_and_times(scraped_results, selected_chart)
        if auspicious_summary:
            st.markdown("## Auspicious Dates and Corresponding Auspicious Times (Basic)")
            df_ausp = pd.DataFrame(auspicious_summary)
            st.dataframe(df_ausp)
        else:
            st.info("No auspicious summary found.")
        
        refined = refine_auspicious_times(scraped_results, selected_chart)
        if refined:
            st.markdown("## True Auspicious Intervals (Intersection)")
            df_refined = pd.DataFrame(refined)
            st.dataframe(df_refined)
        else:
            st.info("No overlapping auspicious intervals found.")
