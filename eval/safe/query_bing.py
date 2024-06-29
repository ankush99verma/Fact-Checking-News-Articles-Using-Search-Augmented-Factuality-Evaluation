import requests
import dataclasses
from common import shared_config

from eval.safe import config as safe_config
NO_RESULT_MSG = 'No good Bing Search result was found'

class BingSearch:
    def __init__(
      self,
      bing_api_key: str,
    ):
      self.bing_api_key = bing_api_key
      self.base_url = f"https://api.bing.microsoft.com/v7.0/search"
    
    def perform_search(self, query: str) -> str:
        assert self.bing_api_key, 'Missing bing_api_key.'

        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        mkt = 'en-US'
        params = { 'q': query, 'mkt': mkt }
        response = requests.get(self.base_url, headers=headers, params=params)
        response.raise_for_status()
    
        search_results = response.json()
    
        if 'webPages' in search_results and 'value' in search_results['webPages']:
          web_pages = search_results['webPages']['value']
          # Convert web page results to BingSearchResult instances
          #bing_results = [GoogleSearchResult(query=query, result=page['snippet']) for page in web_pages if isinstance(page, dict) and 'snippet' in page]
          snippets = [page['snippet'] for page in web_pages if isinstance(page, dict) and 'snippet' in page]

          if not snippets:
            return [NO_RESULT_MSG]

          return ', '.join(snippets)

        return NO_RESULT_MSG
