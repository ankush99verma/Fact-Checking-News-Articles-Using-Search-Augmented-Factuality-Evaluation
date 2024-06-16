from urllib.parse import urlparse
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

from common.shared_config import openai_api_key
from common.shared_config import serper_api_key
from eval.safe import get_atomic_facts
from collections import defaultdict
from eval.safe import classify_relevance
from eval.safe import rate_atomic_fact
from eval.safe.rate_atomic_fact import check_atomic_fact
from eval.safe.classify_relevance import revise_fact
from common.modeling import Model

from collections import defaultdict
import os
import langfun as lf


def clean_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove non-printable characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text


def extract_text_from_url(url):
    try:
        response = requests.get(url)
        # Check if the request was successful
        if response.status_code != 200:
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
        
        return cleaned_text
    except requests.RequestException as e:
        return f"Site cannot be accessed: {e}"


def run_safe(facts_op, model):
   result_dict = defaultdict(dict)
   for sent_id in range(len(facts_op['all_atomic_facts'])):
      sentence_data = facts_op['all_atomic_facts'][sent_id]
      sentence = sentence_data['sentence']
      for atomic_fact in sentence_data['atomic_facts']:
         revised_fact , atomic_fact2 = revise_fact(
            response=sentence, atomic_fact=atomic_fact, model=model
            )
         rate_data, past_steps_dict = check_atomic_fact(
            atomic_fact=revised_fact, rater=model
            )
         result_dict[sent_id][atomic_fact] = {'rate_data': rate_data, 'past_steps_dict':past_steps_dict }
   return result_dict


def get_clean_safe_results(facts_op,model):
   result_dict = run_safe(facts_op, model)
   cleaned_result =  { atomic_fact: result_dict[sent_id][atomic_fact]['rate_data']

                     for sent_id in range(len(facts_op['all_atomic_facts']))
                     for atomic_fact in facts_op['all_atomic_facts'][sent_id]['atomic_facts']
                     
                     }
   return { key : cleaned_result[key].answer for key in cleaned_result.keys() }

# Define helper functions
def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.scheme) and bool(parsed.netloc)

def is_text_length_valid(text, min_length=10):  # minimum length can be adjusted
    return len(text) >= min_length

