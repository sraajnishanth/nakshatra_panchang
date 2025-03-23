import re
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from collections import defaultdict

# ---------------- Load Tharai Charts from JSON File ----------------
@st.cache_data
def load_tharai_charts(json_path="tharais.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

THARAI_CHARTS = load_tharai_charts()

# ------------------ Utility Functions ------------------

def ordinal_suffix(day: int) -> str:
    """Return 'st', 'nd', 'rd', or 'th' for the given day of the month."""
    if 11 <= day % 100 <= 13:
        return "th"
    elif day % 10 == 1:
        return "st"
    elif day % 10 == 2:
        return "nd"
    elif day % 10 == 3:
        return "rd"
    else:
        return "th"

def format_iso_date(iso_date: str) -> str:
    """
    Convert '2025-03-24' into '24th March 2025 - Monday'.
    """
    dobj = datetime.strptime(iso_date, "%Y-%m-%d")
    day = dobj.day
    suffix = ordinal_suffix(day)
    day_str = f"{day}{suffix}"
    month_str = dobj.strftime("%B")
    year_str = dobj.strftime("%Y")
    weekday_str = dobj.strftime("%A")
    return f"{day_str} {month_str} {year_str} - {weekday_str}"

def safe_text(element):
    """Return the stripped text of an element, or '' if element is None."""
    return element.get_text(strip=True) if element else ''

def format_dt(dt):
    """Format a datetime object as 'Apr 24 04:18 AM'."""
    return dt.strftime("%b %d %I:%M %p")

def get_tharai_info(star_name, tharai_chart):
    """
    Given a star_name (e.g. 'Uthiradam') and a Tharai chart,
    return (tharai_name, tharai_meaning) if found, else (None, None).
    """
    star_lower = star_name.lower()
    for entry in tharai_chart:
        for chart_star in entry["nakshatra_names"]:
            if chart_star.lower() == star_lower:
                return entry["tharai"], entry.get("meaning", "")
    return None, None

# ------------------ Parsing Functions ------------------

def parse_datetime_str(date_str, fallback_year):
    """
    Attempts to parse a string like 'Mar 23 03:23 AM' by inserting fallback_year if missing.
    Returns a datetime object.
    """
    pattern_year = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{4}'
    if not re.search(pattern_year, date_str):
        parts = date_str.split()
        if len(parts) >= 2:
            date_str = f"{parts[0]} {parts[1]} {fallback_year} {' '.join(parts[2:])}"
    fmt = "%b %d %Y %I:%M %p"
    return datetime.strptime(date_str, fmt)

def parse_nakshatra_interval(text_line, fallback_year):
    """
    Example: "Uthiradam - Mar 26 03:49 AM – Mar 27 02:29 AM"
    Returns (nakshatra_name, start_dt, end_dt) or None if invalid.
    """
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
    """
    For a day like "2025-03-24" and item {"name": "Abhijit Muhurtham", "time": "11:51 AM – 12:40 PM"}
    return (period_name, start_dt, end_dt) or None if parse fails.
    """
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

def intersect_intervals(a_start, b_start, a_end, b_end):
    """
    Return (start, end) of the intersection or None if no overlap.
    Adjusted parameter order to avoid confusion.
    """
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end > start:
        return (start, end)
    return None

# ------------------ Panchang Data Fetching Functions ------------------

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

def fetch_panchang_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        'primary_header': parse_primary_header(soup),
        'secondary_header': parse_secondary_header(soup),
        'details': parse_data_blocks(soup),
        'gowri_panchang': parse_gowri_panchang(soup),
        'additional_tabs': parse_additional_tabs(soup)
    }
    return data

def fetch_data_from_url(url):
    """Fetch data from a server (URL not shown to user)."""
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Error fetching data from server: {e}")
        return {}
    return fetch_panchang_data(response.text)

def generate_url_for_date(date_obj):
    """Not disclosing the actual source to the user."""
    date_str = date_obj.strftime("%Y-%B-%d").lower()
    return f"https://www.prokerala.com/astrology/tamil-panchangam/{date_str}.html"

def fetch_multiple_days(num_days=5, start_date=None):
    if start_date is None:
        start_date = datetime.today().date()

    all_data = {}
    
    # Create a single placeholder for dynamic status updates
    status_label = st.empty()
    status_label.info("Starting Panchang data fetch...")

    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        url = generate_url_for_date(current_date)
        # Update the same label each iteration instead of creating a new message
        status_label.info(f"Fetching Panchang data for {current_date.isoformat()} ...")
        
        data = fetch_data_from_url(url)
        all_data[current_date.isoformat()] = data

    # Once the loop finishes, show a success message in the same label
    status_label.success("Successfully fetched Panchang data for all dates.")
    
    return all_data


# ------------------- Additional Analysis Functions -------------------

def get_time_periods(fetched_data):
    """
    Extract time period details from Panchang data for blocks with "Period" in the title.
    """
    periods = []
    for day, data in fetched_data.items():
        details = data.get("details", {})
        for title, items in details.items():
            if "period" in title.lower():
                period_type = "Unknown"
                if "auspicious period" in title.lower() and "inauspicious" not in title.lower():
                    period_type = "Auspicious"
                elif "inauspicious period" in title.lower():
                    period_type = "Inauspicious"
                for item in items:
                    if "name" in item and "time" in item:
                        periods.append({
                            "date": day,
                            "period_type": period_type,
                            "period": item["name"],
                            "time": item["time"]
                        })
    return periods

def get_auspicious_dates_and_times(fetched_data, tharai_chart):
    """
    Gather auspicious nakshatras and auspicious periods by day.
    """
    # We'll use the lumps-based approach to get all intervals quickly
    # (not reassigning to actual start date).
    info_list = []
    for day, data in fetched_data.items():
        details = data.get("details", {})
        for title, items in details.items():
            if "nakshatram" in title.lower():
                for item in items:
                    if "name" in item and "time" in item:
                        nak_name = item["name"].strip().lower()
                        for entry in tharai_chart:
                            for chart_nak in entry["nakshatra_names"]:
                                if nak_name == chart_nak.lower():
                                    info_list.append({
                                        "date": day,
                                        "nakshatra": item["name"],
                                        "time": item["time"],
                                        "auspicious": entry["auspicious"]
                                    })
                                    break

    # For each day, if an interval is auspicious, we store it
    ausp_nak_by_day = defaultdict(list)
    for rec in info_list:
        if rec["auspicious"]:
            ausp_nak_by_day[rec["date"]].append(f"{rec['nakshatra']} ({rec['time']})")

    # For time periods
    periods_all = get_time_periods(fetched_data)
    ausp_times_by_day = defaultdict(list)
    for rec in periods_all:
        if rec["period_type"].lower() == "auspicious":
            ausp_times_by_day[rec["date"]].append(f"{rec['period']}: {rec['time']}")

    # Build final list
    result = []
    all_dates = set(list(ausp_nak_by_day.keys()) + list(ausp_times_by_day.keys()))
    for d in sorted(all_dates):
        result.append({
            "date": d,
            "auspicious_nakshatras": ", ".join(ausp_nak_by_day[d]),
            "auspicious_periods": ", ".join(ausp_times_by_day[d])
        })
    return result

def get_nakshatra_auspicious_info_actual_date(fetched_data, tharai_chart):
    """
    Reassign each nakshatra interval to its actual start date, ignoring lumps.
    """
    results = []
    for day, day_data in fetched_data.items():
        fallback_year = day.split("-")[0]
        details = day_data.get("details", {})
        for title, items in details.items():
            if "nakshatram" in title.lower():
                for li in items:
                    if "name" in li and "time" in li:
                        star_name = li["name"].strip()
                        text_line = f"{star_name} - {li['time']}"
                        parsed = parse_nakshatra_interval(text_line, fallback_year)
                        if parsed:
                            nak_name, start_dt, end_dt = parsed
                            actual_day_iso = start_dt.date().isoformat()
                            star_lower = nak_name.lower()
                            star_tharai = None
                            star_ausp = False
                            for entry in tharai_chart:
                                if any(star_lower == s.lower() for s in entry["nakshatra_names"]):
                                    star_tharai = entry["tharai"]
                                    star_ausp = entry["auspicious"]
                                    break
                            results.append({
                                "date": actual_day_iso,
                                "nakshatra": nak_name,
                                "time": li["time"],
                                "tharai": star_tharai if star_tharai else "Unknown Tharai",
                                "auspicious": star_ausp
                            })
    return results

def refine_auspicious_times(fetched_data, tharai_chart):
    """
    Build intervals for auspicious nakshatras (original data grouping).
    Build intervals for Panchang-labeled "Auspicious Period".
    Intersect them. Return a list of records.
    """
    from collections import defaultdict
    nakshatra_intervals = []
    for day, day_data in fetched_data.items():
        fallback_year = day.split("-")[0]
        details = day_data.get("details", {})
        for title, items in details.items():
            if "nakshatram" in title.lower():
                for li in items:
                    if "name" in li and "time" in li:
                        parsed = parse_nakshatra_interval(f"{li['name']} - {li['time']}", fallback_year)
                        if parsed:
                            nak_name, start_dt, end_dt = parsed
                            tharai_name, tharai_meaning = get_tharai_info(nak_name, tharai_chart)
                            if tharai_name:
                                is_ausp = False
                                for entry in tharai_chart:
                                    if entry["tharai"] == tharai_name:
                                        is_ausp = entry["auspicious"]
                                        break
                                if is_ausp:
                                    nakshatra_intervals.append({
                                        "day": day,
                                        "nakshatra_name": nak_name,
                                        "start_dt": start_dt,
                                        "end_dt": end_dt,
                                        "tharai_name": tharai_name,
                                        "tharai_meaning": tharai_meaning
                                    })
    panchang_periods = []
    for day, day_data in fetched_data.items():
        fallback_year = day.split("-")[0]
        details = day_data.get("details", {})
        for title, items in details.items():
            if "auspicious period" in title.lower() and "inauspicious" not in title.lower():
                for li in items:
                    parsed_item = parse_day_period_interval(day, li)
                    if parsed_item:
                        period_name, start_dt, end_dt = parsed_item
                        panchang_periods.append({
                            "day": day,
                            "period_name": period_name,
                            "start_dt": start_dt,
                            "end_dt": end_dt
                        })

    results = []
    nk_by_day = defaultdict(list)
    pp_by_day = defaultdict(list)
    for nk in nakshatra_intervals:
        nk_by_day[nk["day"]].append(nk)
    for pp in panchang_periods:
        pp_by_day[pp["day"]].append(pp)
    all_days = set(nk_by_day.keys()) | set(pp_by_day.keys())
    for d in sorted(all_days):
        for nk in nk_by_day[d]:
            for pp in pp_by_day[d]:
                overlap = intersect_intervals(nk["start_dt"], pp["start_dt"], nk["end_dt"], pp["end_dt"])
                if overlap:
                    s, e = overlap
                    results.append({
                        "date": d,
                        "nakshatra": nk["nakshatra_name"],
                        "tharai_name": nk["tharai_name"],
                        "tharai_meaning": nk["tharai_meaning"],
                        "nakshatra_interval": f"{format_dt(nk['start_dt'])} – {format_dt(nk['end_dt'])}",
                        "panchang_period": pp["period_name"],
                        "period_interval": f"{format_dt(pp['start_dt'])} – {format_dt(pp['end_dt'])}",
                        "start_dt": s
                    })
    return results

# ------------------- Streamlit Dashboard -------------------

st.title("Personalized Nakshatra based Auspicious Times Planner")
st.markdown("""

Discover your optimal moments with this innovative dashboard that calculates auspicious dates and times based on your nakshatra. Whether you’re planning a wedding, launching a business, or scheduling an important ceremony, this tool delivers a day-by-day breakdown of favorable periods tailored just for you. Enjoy a sleek, intuitive interface that presents dates in a clear, reader-friendly format, empowering you to choose the perfect timing for your special occasions.

**How to Use:**
1. **Select Your Nakshatra:** Choose your nakshatra from the dropdown menu.
2. **Set the Date Range:** Pick a start date and specify the number of days to view from the start date.
3. **Get Auspicious Times:** Click the "Get auspicious times" button to fetch your personalized Panchang data.
4. **Review the Analysis:** Explore the analysis tabs to see a detailed breakdown of auspicious intervals and day-by-day summaries.
5. **See the panchang for each date:** You can also see the detailed panchang for each date.
""")

# 1) Let user pick their nakshatra and date range

# Get the list of nakshatras
all_nakshatras = list(THARAI_CHARTS.keys())
all_nakshatras_lower = [s.lower() for s in all_nakshatras]

# Retrieve query parameters using st.query_params (as a property)
query_params = st.query_params

# Extract the 'nakshatra' parameter if present (case insensitive)
# nakshatra_param = query_params.get("nakshatra", [None])[0]
nakshatra_param = None if "nakshatra" not in query_params else query_params["nakshatra"]
st.write(f"Index: {nakshatra_param}")

if nakshatra_param is not None:
    nakshatra_param = nakshatra_param.lower()
    
if nakshatra_param in all_nakshatras_lower:
    default_index = all_nakshatras_lower.index(nakshatra_param)
else:
    default_index = 0

# Create the selectbox with the default index
selected_nakshatra = st.selectbox(
    "Select your nakshatra",
    options=all_nakshatras,
    index=default_index
)


selected_chart = THARAI_CHARTS[selected_nakshatra]

selected_date = st.date_input("Select start date", value=datetime.today().date())
num_days = st.number_input("Enter number of days", min_value=1, max_value=10, value=5, step=1)

# 2) The user clicks "Get auspicious times" to fetch data
if st.button("Get auspicious times"):
    with st.spinner("Fetching Panchang data..."):
        fetched_results = fetch_multiple_days(num_days=num_days, start_date=selected_date)
    st.success("Calculating auspicious times ...")
    
    # Create tabs
    analysis_tab_title = f"{selected_nakshatra}-Auspicious Times"
    day_titles = sorted(fetched_results.keys())
    all_tab_titles = [analysis_tab_title] + day_titles
    tabs = st.tabs(all_tab_titles)

    # === Analysis Tab ===
    with tabs[0]:
        st.header(f"{selected_nakshatra} - Auspicious Times Analysis")

        # A) True Auspicious Intervals (Intersection) - original grouping
        st.subheader("True Auspicious Times based on Nakshatra and Panchang Periods")
        refined = refine_auspicious_times(fetched_results, selected_chart)
        if refined:
            refined_by_date_nak = defaultdict(lambda: defaultdict(list))
            for rec in refined:
                refined_by_date_nak[rec["date"]][rec["nakshatra"]].append(rec)
            for date in sorted(refined_by_date_nak.keys()):
                date_label = format_iso_date(date)
                with st.expander(f"Date: {date_label}", expanded=True):
                    for nak in sorted(refined_by_date_nak[date].keys()):
                        records = refined_by_date_nak[date][nak]
                        records.sort(key=lambda x: x["start_dt"])
                        first = records[0]
                        st.markdown(f"**Nakshatra:** {first['nakshatra']} ({first['tharai_name']}) — {first['tharai_meaning']}")
                        st.markdown(f"**Nakshatra Interval:** {first['nakshatra_interval']}")
                        st.markdown("**Auspicious Periods Overlapping:**")
                        for rec2 in records:
                            st.markdown(f"- **{rec2['panchang_period']}**: {rec2['period_interval']}")
                        st.markdown("---")
        else:
            st.info("No overlapping auspicious intervals found.")

        # B) Basic Nakshatra Analysis - reassign each nakshatra to actual start date
        st.subheader("Basic Nakshatra Analysis (Actual Start Date)")
        nak_info_actual = get_nakshatra_auspicious_info_actual_date(fetched_results, selected_chart)
        # Group by actual date
        date_analysis = defaultdict(lambda: {"intervals": [], "isAusp": False})
        for rec in nak_info_actual:
            d = rec["date"]
            date_analysis[d]["intervals"].append(rec)
            if rec["auspicious"]:
                date_analysis[d]["isAusp"] = True

        # Show each date with "Auspicious" or "Inauspicious"
        for d in sorted(date_analysis.keys()):
            date_label = format_iso_date(d)
            label_str = "Auspicious" if date_analysis[d]["isAusp"] else "Inauspicious"
            with st.expander(f"Date: {date_label} - {label_str}", expanded=True):
                for rec in date_analysis[d]["intervals"]:
                    st.markdown(
                        f"**Nakshatra:** {rec['nakshatra']}  |  "
                        f"**Time:** {rec['time']}  |  "
                        f"**Tharai:** {rec['tharai']}  |  "
                        f"**Auspicious:** {'Yes' if rec['auspicious'] else 'No'}"
                    )
                    st.markdown("---")

        # C) Show the Tharai chart
        st.subheader("Selected Tharai Chart")
        chart_rows = []
        for entry in selected_chart:
            chart_rows.append({
                "Tharai": entry["tharai"],
                "Nakshatra Numbers": ", ".join(str(n) for n in entry["nakshatra_numbers"]),
                "Nakshatra Names": ", ".join(entry["nakshatra_names"]),
                "Meaning": entry.get("meaning", "N/A"),
                "Auspicious": "Yes" if entry["auspicious"] else "No"
            })
        st.table(pd.DataFrame(chart_rows))

        # D) Time Periods
        st.subheader("Basic Time Periods")
        time_periods = get_time_periods(fetched_results)
        if time_periods:
            time_grouped = defaultdict(list)
            for rec in time_periods:
                time_grouped[rec["date"]].append(rec)
            for date in sorted(time_grouped.keys()):
                date_label = format_iso_date(date)
                with st.expander(f"Date: {date_label}", expanded=True):
                    for rec in time_grouped[date]:
                        st.markdown(f"**{rec['period']}**: {rec['time']} (Type: {rec['period_type']})")
                        st.markdown("---")
        else:
            st.info("No period details found.")

        # E) Basic Auspicious Dates and Times Summary
        st.subheader("Auspicious Dates and Corresponding Auspicious Times (Basic)")
        auspicious_summary = get_auspicious_dates_and_times(fetched_results, selected_chart)
        if auspicious_summary:
            for rec in auspicious_summary:
                date_label = format_iso_date(rec["date"])
                with st.expander(f"Date: {date_label}", expanded=True):
                    st.markdown(f"**Auspicious Nakshatras:** {rec['auspicious_nakshatras']}")
                    st.markdown(f"**Auspicious Periods:** {rec['auspicious_periods']}")
        else:
            st.info("No auspicious summary found.")

    # === Daily Panchang Tabs (original grouping) ===
    for i, day in enumerate(day_titles):
        date_label = format_iso_date(day)
        with tabs[i+1]:
            st.subheader(f"Panchang for {date_label}")
            data_for_day = fetched_results[day]

            primary = data_for_day.get("primary_header", {})
            if primary:
                st.markdown("### Primary Details")
                st.markdown(f"**Date:** {primary.get('date','')}")
                st.markdown(f"**Location:** {primary.get('location','')}")
            
            secondary = data_for_day.get("secondary_header", {})
            if secondary:
                st.markdown("### Secondary Details")
                sec_table = pd.DataFrame(list(secondary.items()), columns=["Label", "Value"])
                st.table(sec_table)
            
            details = data_for_day.get("details", {})
            if details:
                st.markdown("### Detailed Panchang Data")
                for title, items in details.items():
                    with st.expander(title, expanded=True):
                        for item in items:
                            if "name" in item and "time" in item:
                                st.markdown(f"- **{item['name']}**: {item['time']}")
                            else:
                                st.write(item.get("text",""))

            gowri = data_for_day.get("gowri_panchang", {})
            if gowri:
                st.markdown("### Gowri Panchangam")
                for tab_id, entries in gowri.items():
                    with st.expander(tab_id, expanded=True):
                        for entry in entries:
                            st.markdown(f"- **{entry['period']}**: {entry['time']} (Status: {entry.get('status','')})")

            additional = data_for_day.get("additional_tabs", {})
            if additional:
                st.markdown("### Additional Information")
                for tab_id, paragraphs in additional.items():
                    with st.expander(tab_id, expanded=True):
                        for para in paragraphs:
                            st.write(para)
