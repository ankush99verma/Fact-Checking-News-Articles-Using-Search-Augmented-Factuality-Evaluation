# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Class for querying the Google Serper API."""

import random
import time
from typing import Any, Optional, Literal

import requests
from eval.safe.search_results import GoogleSearchResult, SearchResultMetadata

_SERPER_URL = 'https://google.serper.dev'
NO_RESULT_MSG = 'No good Google Search result was found'


class SerperAPI:
  """Class for querying the Google Serper API."""

  def __init__(
      self,
      serper_api_key: str,
      gl: str = 'us',
      hl: str = 'en',
      k: int = 1,
      tbs: Optional[str] = None,
      search_type: Literal['news', 'search', 'places', 'images'] = 'search',
      query=None
  ):
    self.serper_api_key = serper_api_key
    self.gl = gl
    self.hl = hl
    self.k = k
    self.tbs = tbs
    self.search_type = search_type
    self.result_key_for_type = {
        'news': 'news',
        'places': 'places',
        'images': 'images',
        'search': 'organic',
    }
    self.query = query

  def run(self, query: str, **kwargs: Any) -> GoogleSearchResult:
    """Run query through GoogleSearch and parse result."""
    assert self.serper_api_key, 'Missing serper_api_key.'
    self.query = query
    results = self._google_serper_api_results(
        query,
        gl=self.gl,
        hl=self.hl,
        num=self.k,
        tbs=self.tbs,
        search_type=self.search_type,
        **kwargs,
    )

    return self._parse_results(results)

  def _google_serper_api_results(
      self,
      search_term: str,
      search_type: str = 'search',
      max_retries: int = 20,
      **kwargs: Any,
  ) -> dict[Any, Any]:
    """Run query through Google Serper."""
    headers = {
        'X-API-KEY': self.serper_api_key or '',
        'Content-Type': 'application/json',
    }
    params = {
        'q': search_term,
        **{key: value for key, value in kwargs.items() if value is not None},
    }
    response, num_fails, sleep_time = None, 0, 0

    while not response and num_fails < max_retries:
      try:
        response = requests.post(
            f'{_SERPER_URL}/{search_type}', headers=headers, params=params
        )
      except AssertionError as e:
        raise e
      except Exception:  # pylint: disable=broad-exception-caught
        response = None
        num_fails += 1
        sleep_time = min(sleep_time * 2, 600)
        sleep_time = random.uniform(1, 10) if not sleep_time else sleep_time
        time.sleep(sleep_time)

    if not response:
      raise ValueError('Failed to get result from Google Serper API')

    response.raise_for_status()
    search_results = response.json()
    return search_results

  def _parse_snippets(self, results: dict) -> GoogleSearchResult:
    """Parse results and return a GoogleSearchResult object."""
    snippets = []
    metadata = []

    if results.get('answerBox'):
        answer_box = results.get('answerBox', {})
        answer = answer_box.get('answer')
        snippet = answer_box.get('snippet')
        snippet_highlighted = answer_box.get('snippetHighlighted')

        if answer and isinstance(answer, str):
            snippets.append(answer)
            metadata.append(SearchResultMetadata(snippet=answer))
        if snippet and isinstance(snippet, str):
            snippets.append(snippet.replace('\n', ' '))
            metadata.append(SearchResultMetadata(snippet=snippet.replace('\n', ' ')))
        if snippet_highlighted:
            snippets.append(snippet_highlighted)
            metadata.append(SearchResultMetadata(snippet=snippet_highlighted))

    if results.get('knowledgeGraph'):
        kg = results.get('knowledgeGraph', {})
        title = kg.get('title')
        entity_type = kg.get('type')
        description = kg.get('description')
        link = kg.get('descriptionLink')

        if entity_type:
            snippet = f'{title}: {entity_type}.'
            snippets.append(snippet)
            metadata.append(SearchResultMetadata(snippet=snippet, url=link, datePublished=None))

        if description:
            snippets.append(description)
            metadata.append(SearchResultMetadata(snippet=description, url=link, datePublished=None))

        for attribute, value in kg.get('attributes', {}).items():
            snippet = f'{title} {attribute}: {value}.'
            snippets.append(snippet)
            metadata.append(SearchResultMetadata(snippet=snippet, url=link, datePublished=None))

    result_key = self.result_key_for_type[self.search_type]

    if result_key in results:
        for result in results[result_key][:self.k]:
            url = result.get('link', '')
            datePublished = result.get('date', '')

            if 'snippet' in result:
                snippets.append(result['snippet'])
                metadata.append(SearchResultMetadata(snippet=result['snippet'], url=url, datePublished=datePublished))


            for attribute, value in result.get('attributes', {}).items():
                snippet = f'{attribute}: {value}.'
                snippets.append(snippet)
                metadata.append(SearchResultMetadata(snippet=snippet, url=url, datePublished=datePublished))

    if not snippets:
        return GoogleSearchResult(query=self.query, result=NO_RESULT_MSG, metadata=[])

    result_snippets = ' '.join(snippets)  # Combine snippets into a single string
    return GoogleSearchResult(query=self.query, result=result_snippets, metadata=metadata)

  def _parse_results(self, results: dict[Any, Any]) -> GoogleSearchResult:
    return self._parse_snippets(results)
