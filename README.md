### **Fact Checking News Articles or any custom text using Search Augmented Factuality Evaluation (SAFE)**
**The project is an extention to SAFE module proposed in the paper below**

Long-form factuality in large language models : https://arxiv.org/abs/2403.18802

## Installation

First, clone our GitHub repository.

```bash
git clone https://github.com/ankush99verma/Fact-Checking-News-Articles-Using-Search-Augmented-Factuality-Evaluation.git
```

Then navigate to the newly-created folder.
```bash
cd long-form-factuality
```

Next, create a new Python 3.10+ environment using `conda`.

```bash
conda create --name longfact python=3.10
```

Activate the newly-created environment.

```bash
conda activate longfact
```

All external package requirements are listed in `requirements.txt`.
To install all packages, and run the following command.

```bash
pip install -r requirements.txt
```

## How to run
To Run the streamlit application:

- Copy-paste OpenAI, Serper API keys in shared_config.py located in `common/`
- run following command in the root directory to start the web application: 
```bash
streamlit run streamlit_app.py
```

## Usage

The Real-Time Fact Check Application is a web-based tool designed to verify the accuracy of information in news articles and other textual content. Utilizing a method called Search-Augmented Factuality Evaluator (SAFE), the application automates the extraction and analysis of smaller constituent facts in the given input fact which are known as atomic facts.
Key features include:
- URL-Based Text Extraction: Extracts and cleans main content from news articles, filtering out advertisements, sponsorships, and irrelevant sections.
- Text Input Processing: Allows direct text input for fact-checking.
- Bulk URL Processing: Supports batch processing of multiple URLs from a .txt file.
- Detailed Fact Analysis: Provides comprehensive fact-checking results, including supported facts and related search results.
- User-Friendly Interface: Offers an intuitive interface with detailed statistics and analysis results.
