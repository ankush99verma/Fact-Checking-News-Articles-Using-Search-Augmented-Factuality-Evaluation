import logging
from urllib.parse import urlparse
from time import sleep
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from common.shared_config import openai_api_key
from common.shared_config import serper_api_key
from eval.safe.rate_atomic_fact import check_atomic_fact
from eval.safe.classify_relevance import revise_fact
from eval.safe import get_atomic_facts
from common.modeling import Model

from collections import defaultdict
import os
import langfun as lf
from typing import Dict, Any
from collections import defaultdict

import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the model
model_name = "openai:gpt-3.5-turbo"
model = Model(model_name=model_name, temperature=0.7, max_tokens=150)

def clean_text(text):
    try:
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove non-printable characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        logging.info("Text cleaned successfully.")
        return text
    except Exception as e:
        logging.error(f"Failed to clean text: {e}")
        return text

def setup_driver():
    """Setup Chrome driver with necessary options."""
    capabilities = DesiredCapabilities().CHROME
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU usage
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def handle_popups(driver):
    """Handle common pop-ups such as GDPR and subscription prompts."""
    try:
        gdpr_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "gdpr-banner__accept"))
        )
        ActionChains(driver).move_to_element(gdpr_accept_button).click(gdpr_accept_button).perform()
    except Exception as e:
        logging.info(f"No GDPR pop-up found: {e}")

    try:
        close_news_popup = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "my-news-landing-popup__icon-close"))
        )
        ActionChains(driver).move_to_element(close_news_popup).click(close_news_popup).perform()
    except Exception as e:
        logging.info(f"No subscription pop-up found: {e}")

def extract_text_from_url(url):
    driver = setup_driver()
    driver.get(url)
    driver.implicitly_wait(10)

    handle_popups(driver)
    
    sleep(5)  # Wait for the page to load

    raw_soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # Extract the main article text
    try:
        json_dictionaries = raw_soup.find_all(name='script', attrs={'type': 'application/ld+json'})
        for json_dictionary in json_dictionaries:
            dictionary = json.loads("".join(json_dictionary.contents), strict=False)
            if 'articleBody' in dictionary:
                return dictionary['articleBody']
    except Exception as e:
        logging.error(f"Failed to extract article body from JSON: {e}")

    # Fallback to extracting from main content
    try:
        article = raw_soup.find('article')
        if article:
            return article.get_text(separator=' ')
        
        paragraphs = raw_soup.find_all('p')
        main_text = ' '.join([p.get_text(separator=' ') for p in paragraphs])
        return main_text
    except Exception as e:
        logging.error(f"Failed to extract text from HTML content: {e}")
        return "Failed to extract article text"

# Filter advertisements
def filter_advertisements(text):
    """Filter out advertisement sections from the text."""
    ad_keywords = ['advertisement', 'sponsored content', 'sponsored post']
    lines = text.split('\n')
    filtered_lines = [line for line in lines if not any(ad_keyword in line.lower() for ad_keyword in ad_keywords)]
    return '\n'.join(filtered_lines)


def run_safe(facts_op, model):
    result_dict = defaultdict(dict)
    futures = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for sent_id, sentence_data in enumerate(facts_op['all_atomic_facts']):
            for atomic_fact in sentence_data['atomic_facts']:
                future = executor.submit(process_fact, sentence_data['sentence'], atomic_fact, model)
                futures.append((sent_id, atomic_fact, future))
        
        for sent_id, atomic_fact, future in futures:
            try:
                rate_data, search_dicts = future.result()
                result_dict[sent_id][atomic_fact] = {'rate_data': rate_data, 'search_dicts': search_dicts}
                logging.info(f"Processed fact {atomic_fact} for sentence {sent_id}.")
            except Exception as e:
                logging.error(f"Failed to process fact {atomic_fact} for sentence {sent_id}: {e}")
    return result_dict

def get_clean_safe_results(facts_op, model):
    try:
        
        result_dict = run_safe(facts_op, model)
        
        if result_dict is None:
            logging.error("run_safe returned None")
            return {}, {}
        else:
            cleaned_result = {
                atomic_fact: result_dict[sent_id][atomic_fact]['rate_data']
                for sent_id in range(len(facts_op['all_atomic_facts']))
                for atomic_fact in facts_op['all_atomic_facts'][sent_id]['atomic_facts']
            }
            
            search_results_raw = {
                atomic_fact: result_dict[sent_id][atomic_fact]['search_dicts']['google_searches']
                for sent_id in range(len(facts_op['all_atomic_facts']))
                for atomic_fact in facts_op['all_atomic_facts'][sent_id]['atomic_facts']
            }
            
            clean_results = {key: cleaned_result[key].answer if cleaned_result[key] is not None else None for key in cleaned_result.keys()}
            search_results = {key: search_results_raw[key] if search_results_raw[key] is not None else [] for key in search_results_raw.keys()}
            
            logging.info("Results cleaned and prepared.")
            return clean_results, search_results
    except Exception as e:
        logging.error(f"Error in getting clean safe results: {e}")
        return {}

def process_fact(sentence, atomic_fact, model):
    try:
        revised_fact, _ = revise_fact(response=sentence, atomic_fact=atomic_fact, model=model)
        final_answer, search_dicts = check_atomic_fact(atomic_fact=revised_fact, rater=model)
        logging.info(f"Fact {atomic_fact} processed.")
        return final_answer, search_dicts
    except Exception as e:
        logging.error(f"Error processing fact {atomic_fact}: {e}")
        return None, None

def process_bulk_urls(url_list):
    bulk_results = []
    for url in url_list:
        if is_valid_url(url):
            try:
                extracted_text = extract_text_from_url(url)
                if extracted_text:
                    filtered_text = filter_advertisements(extracted_text)
                    facts_op = get_atomic_facts.main(filtered_text, model)
                    clean_results, search_dicts = get_clean_safe_results(facts_op, model)
                    bulk_results.append((url, extracted_text, clean_results, search_dicts))
                    logging.info(f"Processed URL: {url}")
                else:
                    logging.error(f"Failed to extract text from URL: {url}")
                    bulk_results.append((url, "", {}, {}))
            except Exception as e:
                logging.error(f"Failed to process URL {url}: {e}")
                bulk_results.append((url, "", {}, {}))
        else:
            logging.warning(f"Invalid URL skipped: {url}")
            bulk_results.append((url, "", {}, {}))
    return bulk_results

# Define helper functions
def is_valid_url(url):
    parsed = urlparse(url)
    # Check if the scheme is in a list of allowed schemes
    valid_schemes = ['http', 'https', 'ftp', 'ftps']
    return parsed.scheme in valid_schemes and bool(parsed.netloc)

def is_text_length_valid(text, min_length=10):  # minimum length can be adjusted
    return len(text) >= min_length

