import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time  # Import the time module

from common.shared_config import openai_api_key
from common.shared_config import serper_api_key
from eval.safe import get_atomic_facts
from collections import defaultdict
from eval.safe import classify_relevance
from eval.safe import rate_atomic_fact
from eval.safe.rate_atomic_fact import check_atomic_fact
from eval.safe.classify_relevance import revise_fact
from common.modeling import Model

from streamlit_app_helper import run_safe, extract_text_from_url, clean_text, get_clean_safe_results, is_valid_url, is_text_length_valid

from collections import defaultdict
import os
import langfun as lf

os.environ['OPENAI_API_KEY'] = openai_api_key
os.environ['SERPER_API_KEY'] = serper_api_key


# Initialize the model
model_name = "openai:gpt-3.5-turbo"

# Create an instance of the Model class
model = Model(model_name=model_name, temperature=0.7, max_tokens=150)

# Streamlit app
st.title('Real-Time Fact Check Application')

# Define sections
url_section = st.expander("Enter URL of public news article you wnat to fact check")
text_entry_section = st.expander("Copy Paste text you want to fact check")
text_typing_section = st.expander("Type out text you want to fact check")

# Variables to store the extracted or entered text
extracted_text = ""
entered_text = ""
typed_text = ""

# Web Text Extractor section
with url_section:
    url = st.text_input('Enter URL of the website')
    if st.button('Extract Text'):
        if url and is_valid_url(url):
            extracted_text = extract_text_from_url(url)
            extracted_text = extracted_text[:100]
            st.session_state['input_text'] = extracted_text
            facts_op = get_atomic_facts.main(extracted_text, model)
            st.session_state['output_text'] = get_clean_safe_results(facts_op, model)
            st.experimental_rerun()
        else:
            st.error('Please enter a valid URL')

# Customer Text Entering section
with text_entry_section:
    entered_text = st.text_area('Paste your text here')
    if st.button('Submit Pasted Text'):
        if entered_text:
            start_time = time.time()  # Start timing

            st.session_state['input_text'] = entered_text
            text_set_time = time.time()  # Time after setting text
            print(f"Time to set text: {text_set_time - start_time:.2f} seconds")

            facts_op = get_atomic_facts.main(entered_text, model)
            facts_time = time.time()  # Time after getting facts
            print(f"Time to get atomic facts: {facts_time - text_set_time:.2f} seconds")

            if facts_op.get('num_claims', 0) == 0:    
                st.error('No atomic facts found in the text')
                st.stop()

            st.session_state['output_text'] = get_clean_safe_results(facts_op, model)
            clean_results_time = time.time()  # Time after cleaning results
            print(f"Time to clean results: {clean_results_time - facts_time:.2f} seconds")

            st.experimental_rerun()
            rerun_time = time.time()  # Time after rerun
            print(f"Time to rerun: {rerun_time - clean_results_time:.2f} seconds")

        else:
            st.error('Please enter text')

# Customer Typing section
with text_typing_section:
    typed_text = st.text_area('Type your text here')
    if st.button('Submit Typed Text'):
        if typed_text and is_text_length_valid(typed_text):
            st.session_state['input_text']  = typed_text
            facts_op = get_atomic_facts.main(typed_text, model)
            st.session_state['output_text'] = get_clean_safe_results(facts_op, model)
            st.experimental_rerun()
        else:
            st.error('Please enter text with sufficient length')
# Display output text
if 'output_text' in st.session_state:
    st.header('Input Text')
    st.text_area('Extracted/Entered Text', st.session_state['input_text'], height=150)

    st.header('Fact Check Results')

    # Convert the output dictionary to a pandas DataFrame for better display
    facts_df = pd.DataFrame(list(st.session_state['output_text'].items()), columns=['Fact', 'Support'])

    # Display the DataFrame in a tabular format
    st.dataframe(facts_df)

    # Calculate statistics
    total_facts = len(facts_df)
    supported_facts = facts_df[facts_df['Support'] == 'Supported'].shape[0]
    percentage_supported = (supported_facts / total_facts) * 100 if total_facts > 0 else 0

    # Display statistics
    st.header('Statistics')
    st.write(f"Total Facts: {total_facts}")
    st.write(f"Supported Facts: {supported_facts}")
    st.write(f"Percentage of Supported Facts: {percentage_supported:.2f}%")

