import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime, timedelta

st.set_page_config(page_title="Live Rechtspraak Scraper", layout="wide")

if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []
if 'scrape_in_progress' not in st.session_state:
    st.session_state.scrape_in_progress = False
if 'stop_scraping' not in st.session_state:
    st.session_state.stop_scraping = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'results_container' not in st.session_state:
    st.session_state.results_container = st.empty()

def scrape_rechtspraak(num_rulings=100, court_filter=None, start_date=None, end_date=None, keyword=None):
    base_url = "https://uitspraken.rechtspraak.nl/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9"
    }
    
    max_retries = 3
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while len(st.session_state.scraped_data) < num_rulings and not st.session_state.stop_scraping:
        try:
            progress = min(len(st.session_state.scraped_data)/num_rulings, 0.99)
            progress_bar.progress(progress)
            status_text.text(f"Scraping page {st.session_state.current_page} - Found {len(st.session_state.scraped_data)}/{num_rulings} rulings")
            
            url = f"{base_url}/?page={st.session_state.current_page}"
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=25)
                    response.raise_for_status()
                    break
                except:
                    if attempt < max_retries - 1:
                        delay = random.uniform(5, 15)
                        status_text.text(f"Retrying page {st.session_state.current_page} in {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        st.warning(f"Skipping page {st.session_state.current_page}")
                        st.session_state.current_page += 1
                        break
            
            if not response or not response.ok:
                st.session_state.current_page += 1
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            rulings = soup.find_all("div", class_="result")
            
            if not rulings:
                status_text.text("No more rulings found")
                break
            
            for ruling in rulings:
                if len(st.session_state.scraped_data) >= num_rulings or st.session_state.stop_scraping:
                    break
                
                try:
                    link = ruling.find("a", href=True)['href']
                    ecli = link.split('=')[-1] if '=' in link else link.split('/')[-1]
                    title = ruling.find("h3").get_text(strip=True) if ruling.find("h3") else "No title"
                    date = ruling.find("span", class_="date").get_text(strip=True) if ruling.find("span", class_="date") else "Unknown"
                    court = ruling.find("span", class_="court").get_text(strip=True) if ruling.find("span", class_="court") else "Unknown"
                    
                    if court_filter and court_filter.lower() not in court.lower():
                        continue
                    if start_date and date < start_date:
                        continue
                    if end_date and date > end_date:
                        continue
                    if keyword and keyword.lower() not in title.lower():
                        continue
                    
                    full_text = ""
                    detail_url = base_url + link if not link.startswith('http') else link
                    
                    for _ in range(2):
                        try:
                            detail_response = requests.get(detail_url, headers=headers, timeout=25)
                            detail_response.raise_for_status()
                            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                            full_text_element = detail_soup.find("div", class_="full-text")
                            full_text = full_text_element.get_text(strip=True) if full_text_element else "No full text"
                            break
                        except:
                            full_text = "Error loading text"
                            time.sleep(random.uniform(3, 8))
                    
                    new_ruling = {
                        "ECLI": ecli,
                        "Date": date,
                        "Court": court,
                        "Title": title,
                        "Text Preview": full_text[:500] + "..." if len(full_text) > 500 else full_text
                    }
                    
                    st.session_state.scraped_data.append(new_ruling)
                    df = pd.DataFrame(st.session_state.scraped_data)
                    st.session_state.results_container.dataframe(df)
                    
                    time.sleep(random.uniform(1, 3))
                except:
                    continue
            
            st.session_state.current_page += 1
            time.sleep(random.uniform(3, 6))
        except:
            continue
    
    progress_bar.progress(1.0)
    status_text.empty()
    return st.session_state.scraped_data

# UI Setup
st.title("⚖️ Live Rechtspraak.nl Scraper")

with st.sidebar:
    st.header("Settings")
    num_rulings = st.slider("Number of rulings", 10, 1000, 100)
    court_filter = st.text_input("Court filter", "rechtbank")
    start_date = st.text_input("Start date (YYYY-MM-DD)", (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"))
    end_date = st.text_input("End date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
    keyword = st.text_input("Keyword in title", "arbeid")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Scraping", type="primary"):
            st.session_state.scrape_in_progress = True
            st.session_state.stop_scraping = False
            st.session_state.scraped_data = []
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("Stop Scraping", type="secondary"):
            st.session_state.stop_scraping = True
            st.session_state.scrape_in_progress = False

# Main display
if st.session_state.scrape_in_progress:
    with st.spinner("Scraping in progress..."):
        scrape_rechtspraak(
            num_rulings=num_rulings,
            court_filter=court_filter,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword
        )
        st.session_state.scrape_in_progress = False
        st.success("Scraping completed!")

if st.session_state.scraped_data:
    st.subheader(f"Results ({len(st.session_state.scraped_data)} rulings)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download JSON",
            data=json.dumps(st.session_state.scraped_data, indent=2, ensure_ascii=False),
            file_name="rechtspraak_data.json",
            mime="application/json"
        )
    with col2:
        st.download_button(
            label="Download CSV",
            data=pd.DataFrame(st.session_state.scraped_data).to_csv(index=False),
            file_name="rechtspraak_data.csv",
            mime="text/csv"
        )
elif not st.session_state.scrape_in_progress:
    st.info("Configure settings and click 'Start Scraping' to begin")