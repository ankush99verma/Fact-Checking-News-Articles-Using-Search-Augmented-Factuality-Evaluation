import logging
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from common.shared_config import openai_api_key
from common.shared_config import serper_api_key
from eval.safe.rate_atomic_fact import check_atomic_fact
from eval.safe.classify_relevance import revise_fact
import langfun as lf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        # Check if the request was successful
        if response.status_code != 200:
            logging.error(f"Failed to access site: HTTP {response.status_code}")
            return "Site cannot be accessed"
        
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove tail elements
        tail_elements = soup.find_all(['aside', 'footer', 'nav', 'section'])
        for element in tail_elements:
            element.decompose()
        
        # Remove elements with specific classes or ids that are known to be tail elements
        unwanted_classes = ['more-options', 'more-news', 'also-see', 'related-articles']
        for unwanted_class in unwanted_classes:
            for element in soup.find_all(class_=unwanted_class):
                element.decompose()
        
        unwanted_ids = ['more-options', 'more-news', 'also-see', 'related-articles']
        for unwanted_id in unwanted_ids:
            for element in soup.find_all(id=unwanted_id):
                element.decompose()

        # Extract the header (usually in <h1> tag)
        header = soup.find('h1')
        header_text = header.get_text(separator=' ') if header else ''
        # Extract the main content (usually in <p> tags)
        paragraphs = soup.find_all('p')
        main_text = ' '.join([p.get_text(separator=' ') for p in paragraphs])
        # Combine header and main text
        full_text = f"{header_text} {main_text}"
        # Clean the extracted text
        cleaned_text = clean_text(full_text)
        logging.info("Text extracted and cleaned from URL.")
        return cleaned_text
    except requests.RequestException as e:
        logging.error(f"Error accessing URL: {e}")
        return f"Site cannot be accessed: {e}"

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
        cleaned_result = {
            atomic_fact: result_dict[sent_id][atomic_fact]['rate_data']
            for sent_id in range(len(facts_op['all_atomic_facts']))
            for atomic_fact in facts_op['all_atomic_facts'][sent_id]['atomic_facts']
        }
        clean_results = {key: cleaned_result[key].answer if cleaned_result[key] is not None else None for key in cleaned_result.keys()}
        
        search_results = {
        atomic_fact: result_dict[sent_id][atomic_fact]['search_dicts']['google_searches']
        for sent_id in range(len(facts_op['all_atomic_facts']))
        for atomic_fact in facts_op['all_atomic_facts'][sent_id]['atomic_facts']
        }

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

# Define helper functions
def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.scheme) and bool(parsed.netloc)

def is_text_length_valid(text, min_length=10):  # minimum length can be adjusted
    return len(text) >= min_length

