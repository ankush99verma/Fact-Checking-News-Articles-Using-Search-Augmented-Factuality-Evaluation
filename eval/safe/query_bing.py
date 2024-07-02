import requests
import dataclasses
from common import shared_config
from typing import Tuple, List, Dict, Optional
from eval.safe.search_results import GoogleSearchResult, SearchResultMetadata

from eval.safe import config as safe_config
NO_RESULT_MSG = 'No good Bing Search result was found'

class BingSearch:
    def __init__(
      self,
      bing_api_key: str,
    ):
      self.bing_api_key = bing_api_key
      self.base_url = f"https://api.bing.microsoft.com/v7.0/search"
    
    def perform_search(self, query: str) -> GoogleSearchResult:
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {'q': query, 'mkt': 'en-US'}
        response = requests.get(self.base_url, headers=headers, params=params)
        response.raise_for_status()

        search_results = response.json()
        metadata = []

        if 'webPages' in search_results and 'value' in search_results['webPages']:
            web_pages = search_results['webPages']['value']
            snippets = []
            for page in web_pages:
                if 'snippet' in page:
                    snippets.append(page['snippet'])
                    # Collecting metadata for each page
                    page_metadata = SearchResultMetadata(
                        snippet=page.get('snippet', 'No snippet'),
                        url=page.get('url', 'No URL'),
                        datePublished=page.get('datePublished', 'No date')
                    )
                    metadata.append(page_metadata)
            
            if snippets:
                result_snippets = ', '.join(snippets)
                return GoogleSearchResult(query=query, result=result_snippets, metadata=metadata)
            else:
                return GoogleSearchResult(query=query, result='No snippets found')
        else:
            return GoogleSearchResult(query=query, result='No results found')
