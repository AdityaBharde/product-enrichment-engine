from pydantic import BaseModel
from typing import List

class SourceCandidate(BaseModel):
   
    url: str
    title: str
    snippet: str
    domain: str
    source_type: str
    authority_score: float
    relevance_score: float
    exact_mpn_match: bool
    manufacturer_domain_match: bool
    discovery_query: str
    rank: int = 0  # 0 indicates unranked

class SourceDiscoveryResult(BaseModel):
    product_mpn: str
    status: str
    sources: List[SourceCandidate]