import os
import json
import re
import urllib.parse
from typing import List, Dict

from app.models.product_profile import ProductProfile
from app.models.source import SourceCandidate, SourceDiscoveryResult
from app.services.search_client import SearchClient, SearchResult

# Configurable Limits
MAX_QUERIES_PER_PRODUCT = 3
MAX_RESULTS_PER_QUERY = 5
MAX_FINAL_SOURCES = 10

# Configurable Weights
AUTHORITY_WEIGHT = 0.6
RELEVANCE_WEIGHT = 0.4

# Known Domains for Entity Resolution (Simulated Database)
KNOWN_MANUFACTURER_DOMAINS = {
    "Jam Industrial Supply": "jamindustrialsupply.com",
    "Freud Inc": "freudtools.com",
    "3M": "3m.com",
    "Black & Decker": "blackanddecker.com"
}

# Domain Filters
KNOWN_DISTRIBUTORS = ["mscdirect.com", "grainger.com", "fastenal.com", "digikey.com"]
USELESS_DOMAINS = ["google.com", "bing.com", "facebook.com", "twitter.com", "pinterest.com"]

# NEW: Strict E-Commerce / Marketplace Blocklist
BLOCKED_ECOM_DOMAINS = [
    "amazon.com", "amazon.in", "ebay.com", "walmart.com", "alibaba.com", 
    "aliexpress.com", "homedepot.com", "lowes.com", "target.com",
    "etsy.com", "wayfair.com", "indiamart.com", "flipkart.com"
]

def normalize_url(url: str) -> str:
    """Removes trailing slashes, tracking parameters, and www to enable exact deduplication."""
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.replace("www.", "")
    clean_url = f"{parsed.scheme}://{netloc}{parsed.path}"
    return clean_url.rstrip("/")

def filter_result(result: SearchResult) -> bool:
    """Returns True if the result is valid, False if it is blocked."""
    if not result.url or not result.domain:
        return False
        
    domain_lower = result.domain.lower()
    
    # 1. Block search engines & social media
    if any(useless in domain_lower for useless in USELESS_DOMAINS):
        return False
        
    # 2. Block all E-Commerce platforms (Hackathon Requirement)
    if any(ecom in domain_lower for ecom in BLOCKED_ECOM_DOMAINS):
        return False
        
    return True

def check_exact_mpn(mpn: str, text: str) -> bool:
    """Uses word boundaries to check if the EXACT MPN appears in the text."""
    if not mpn or not text:
        return False
    pattern = r'\b' + re.escape(mpn) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))

def classify_source(url: str, domain: str, mfg_domain: str) -> str:
    """Deterministic source classification based on domain and URL patterns."""
    url_lower = url.lower()
    domain_lower = domain.lower()
    
    # Strip query params to reliably check extensions
    clean_path = urllib.parse.urlparse(url_lower).path
    
    is_mfg = (mfg_domain and mfg_domain.lower() in domain_lower)
    
    if is_mfg:
        if clean_path.endswith(".pdf") or "document" in url_lower or "manual" in url_lower:
            return "manufacturer_document"
        elif "catalog" in url_lower:
            return "manufacturer_catalog"
        else:
            return "manufacturer_product_page"
            
    if any(dist in domain_lower for dist in KNOWN_DISTRIBUTORS):
        return "distributor"
        
    return "unknown"

def get_authority_score(source_type: str) -> float:
    """Deterministic authority scoring based on source classification."""
    scores = {
        "manufacturer_product_page": 1.0,
        "manufacturer_document": 0.95,
        "manufacturer_catalog": 0.90,
        "authorized_distributor": 0.70,
        "distributor": 0.50,
        "unknown": 0.10
    }
    return scores.get(source_type, 0.10)

def discover_sources(profile: ProductProfile, search_client: SearchClient = None) -> SourceDiscoveryResult:
    """
    Core Source Discovery execution flow:
    SearchPlan -> Execute -> Deduplicate -> Classify -> Score -> Rank
    """
    if not search_client:
        search_client = SearchClient()
        
    if not profile.search_plan or not profile.search_plan.search_queries:
        return SourceDiscoveryResult(product_mpn=profile.mpn, status="no_acceptable_sources", sources=[])

    queries_to_run = profile.search_plan.search_queries[:MAX_QUERIES_PER_PRODUCT]
    raw_results = []
    
    # 1. Execute Small Query Set
    for query in queries_to_run:
        results = search_client.search(query, max_results=MAX_RESULTS_PER_QUERY)
        for r in results:
            raw_results.append((query, r))
            
    # 2. Deduplicate and Filter
    seen_urls = set()
    candidates = []
    
    mfg_domain = KNOWN_MANUFACTURER_DOMAINS.get(profile.manufacturer_canonical, "")

    for query, result in raw_results:
        clean_url = normalize_url(result.url)
        
        if clean_url in seen_urls:
            continue
            
        if not filter_result(result):
            print(f"    [BLOCKED E-COM] Dropped result from: {result.domain}")
            continue
            
        seen_urls.add(clean_url)
        
        # 3. Assess Relevance Signals
        exact_mpn_url = check_exact_mpn(profile.mpn, result.url)
        exact_mpn_title = check_exact_mpn(profile.mpn, result.title)
        exact_mpn_snippet = check_exact_mpn(profile.mpn, result.snippet)
        exact_mpn_match = exact_mpn_url or exact_mpn_title or exact_mpn_snippet
        
        manufacturer_domain_match = bool(mfg_domain and mfg_domain.lower() in result.domain.lower())
        
        # 4. Classify Source
        source_type = classify_source(result.url, result.domain, mfg_domain)
        
        # 5. Calculate Authority Score
        auth_score = get_authority_score(source_type)
        
        # 6. Calculate Relevance Score (Heuristic)
        rel_score = 0.1
        if exact_mpn_url or exact_mpn_title:
            rel_score += 0.5
        elif exact_mpn_snippet:
            rel_score += 0.3
            
        if manufacturer_domain_match:
            rel_score += 0.3
            
        rel_score = min(rel_score, 1.0)
        
        candidates.append(SourceCandidate(
            url=result.url,
            title=result.title,
            snippet=result.snippet,
            domain=result.domain,
            source_type=source_type,
            authority_score=auth_score,
            relevance_score=rel_score,
            exact_mpn_match=exact_mpn_match,
            manufacturer_domain_match=manufacturer_domain_match,
            discovery_query=query,
            rank=0
        ))
        
    if not candidates:
        return SourceDiscoveryResult(product_mpn=profile.mpn, status="no_acceptable_sources", sources=[])
        
    # 7. Final Ranking (Manufacturer-first strategy)
    def calculate_final_score(c: SourceCandidate) -> float:
        return (AUTHORITY_WEIGHT * c.authority_score) + (RELEVANCE_WEIGHT * c.relevance_score)

    candidates.sort(key=calculate_final_score, reverse=True)
    
    top_candidates = candidates[:MAX_FINAL_SOURCES]
    for idx, candidate in enumerate(top_candidates, start=1):
        candidate.rank = idx
        
    discovery_result = SourceDiscoveryResult(
        product_mpn=profile.mpn,
        status="success",
        sources=top_candidates
    )
    
    # 8. Save Results
    save_dir = os.path.join("data", "processed", "source_discovery")
    os.makedirs(save_dir, exist_ok=True)
    
    safe_mpn = "".join(c if c.isalnum() else "_" for c in profile.mpn)
    file_path = os.path.join(save_dir, f"{safe_mpn}.json")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(discovery_result.model_dump_json(indent=2))
        
    return discovery_result
