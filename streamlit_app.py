import streamlit as st
import pandas as pd
import logging
from common.shared_config import openai_api_key
from common.shared_config import serper_api_key
from eval.safe import get_atomic_facts
from common.modeling import Model
import io
from streamlit_app_helper import extract_text_from_url, get_clean_safe_results, is_valid_url
import os


os.environ['OPENAI_API_KEY'] = openai_api_key
os.environ['SERPER_API_KEY'] = serper_api_key


# Initialize the model
model_name = "openai:gpt-3.5-turbo"
model = Model(model_name=model_name, temperature=0.7, max_tokens=150)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Streamlit app setup
st.title('Real-Time Fact Check Application')

# Define sections
url_section = st.expander("Enter URL of public news article you want to fact check")
text_entry_section = st.expander("Copy Paste text you want to fact check")
bulk_url_section = st.expander("Upload file with line-separated URLs for bulk processing")


# Bulk URL processing section
with bulk_url_section:
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        url_list = stringio.read().split()
        bulk_results = []
        for url in url_list:
            if is_valid_url(url):
                try:
                    extracted_text = extract_text_from_url(url)
                    facts_op = get_atomic_facts.main(extracted_text, model)
                    clean_results, search_dicts = get_clean_safe_results(facts_op, model)
                    bulk_results.append((url, clean_results, search_dicts))
                    logging.info(f"Processed URL: {url}")
                except Exception as e:
                    logging.error(f"Failed to process URL {url}: {e}")
                    bulk_results.append((url, {}, {}))
            else:
                logging.warning(f"Invalid URL skipped: {url}")
                bulk_results.append((url, {}, {}))
        # Store results in session state and display
        st.session_state['bulk_results'] = bulk_results

# Web Text Extractor section
with url_section:
    url = st.text_input('Enter URL of the website')
    if st.button('Extract Text'):
        if url and is_valid_url(url):
            try:
                extracted_text = extract_text_from_url(url)
                st.session_state['input_text'] = extracted_text
                facts_op = get_atomic_facts.main(extracted_text, model)
                clean_results, search_dicts = get_clean_safe_results(facts_op, model)
                st.session_state['output_text'] = (clean_results, search_dicts)
                st.experimental_rerun()
                logging.info("Text extracted and processed successfully.")
            except Exception as e:
                logging.error(f"Failed to extract or process text: {e}")
                st.error('Failed to extract or process text')
        else:
            logging.warning("Invalid URL provided.")
            st.error('Please enter a valid URL')

# Customer Text Entering section
with text_entry_section:
    entered_text = st.text_area('Paste your text here')
    if st.button('Submit Pasted Text'):
        if entered_text:
            try:
                st.session_state['input_text'] = entered_text
                facts_op = get_atomic_facts.main(entered_text, model)
                clean_results, search_dicts = get_clean_safe_results(facts_op, model)
                st.session_state['output_text'] = (clean_results, search_dicts)
                st.experimental_rerun()
                logging.info("Text submission processed successfully.")
            except Exception as e:
                logging.error(f"Failed to process submitted text: {e}")
                st.error('Failed to process submitted text')
        else:
            logging.warning("No text entered.")
            st.error('Please enter text')

# Display output text based on input type
if 'output_text' in st.session_state and 'input_text' in st.session_state:
    st.header('Input Text')
    st.text_area('Extracted/Entered Text', st.session_state['input_text'], height=150)
    st.header('Fact Check Results')
    clean_results, search_dicts = st.session_state['output_text']
    facts_df = pd.DataFrame(list(clean_results.items()), columns=['Fact', 'Support'])
    search_df = pd.DataFrame(list(search_dicts.items()), columns=['Fact', 'Search Results'])
    search_df['Search Results'] = search_df['Search Results'].apply(lambda x: ', '.join([f"Query: {res['query']}, Result: {res['result']}" for res in x]))
    combined_df = pd.merge(facts_df, search_df, on='Fact', how='left')
    st.dataframe(combined_df)
    total_facts = len(combined_df)
    supported_facts = combined_df[combined_df['Support'] == 'Supported'].shape[0]
    percentage_supported = (supported_facts / total_facts) * 100 if total_facts > 0 else 0
    st.header('Statistics')
    st.write(f"Total Facts: {total_facts}")
    st.write(f"Supported Facts: {supported_facts}")
    st.write(f"Percentage of Supported Facts: {percentage_supported:.2f}%")


elif 'bulk_results' in st.session_state:
    # Display detailed facts and statistics for each URL
    for url, clean_results, search_dicts in bulk_results:
        st.subheader(f'Results for URL: {url}')
        facts_df = pd.DataFrame(list(clean_results.items()), columns=['Fact', 'Support'])
        search_df = pd.DataFrame(list(search_dicts.items()), columns=['Fact', 'Search Results'])
        search_df['Search Results'] = search_df['Search Results'].apply(lambda x: ', '.join([f"Query: {res['query']}, Result: {res['result']}" for res in x]))
        combined_df = pd.merge(facts_df, search_df, on='Fact', how='left')
        st.dataframe(combined_df)
        total_facts = len(combined_df)
        supported_facts = combined_df[combined_df['Support'] == 'Supported'].shape[0]
        percentage_supported = (supported_facts / total_facts) * 100 if total_facts > 0 else 0
        st.write(f"Total Facts: {total_facts}")
        st.write(f"Supported Facts: {supported_facts}")
        st.write(f"Percentage of Supported Facts: {percentage_supported:.2f}%")
