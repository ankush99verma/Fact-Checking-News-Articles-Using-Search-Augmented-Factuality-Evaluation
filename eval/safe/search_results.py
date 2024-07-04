from typing import Dict, List, Optional
import dataclasses

@dataclasses.dataclass()
class SearchResultMetadata:
    snippet: str
    url: str
    datePublished: str

@dataclasses.dataclass()
class GoogleSearchResult:
  query: str
  result: str
  metadata: Optional[SearchResultMetadata] = None  # Maps ID to metadata

  def __init__(self, query: str, result: str, metadata: Optional[List[SearchResultMetadata]] = None):
    self.query = query
    self.result = result
    self.metadata = metadata or []
