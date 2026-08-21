import os
from app.models.product_profile import ProductProfile, SearchPlan
from app.models.source import SourceDiscoveryResult
from app.services.search_client import SearchResult
from app.services.source_discovery import (
    discover_sources,
    normalize_url,
    check_exact_mpn,
    classify_source,
    filter_result
)

class MockSearchClient:
    """Mocks the SearchClient so we don't hit live APIs during unit tests."""
    def search(self, query: str, max_results: int = 5):
        # Fake results simulating a manufacturer PDF, a BLOCKED marketplace, and a duplicate PDF
        return [
            SearchResult(
                url="https://www.freudtools.com/products/DCB518.pdf?utm=test",
                title="DCB518ASTS06G Specifications",
                snippet="Official spec sheet for DCB518ASTS06G.",
                domain="freudtools.com"
            ),
            SearchResult(
                url="https://amazon.com/dp/B00123",
                title="Sanding Belt Freud",
                snippet="Buy DCB518ASTS06G here.",
                domain="amazon.com" # THIS MUST BE BLOCKED NOW
            ),
            SearchResult(
                url="https://flipkart.com/dp/123",
                title="Flipkart listing",
                snippet="Flipkart 123.",
                domain="flipkart.com" # THIS MUST BE BLOCKED NOW
            ),
            SearchResult(
                url="https://freudtools.com/products/DCB518.pdf",
                title="DCB518ASTS06G Specifications",
                snippet="Official spec sheet.",
                domain="freudtools.com" # THIS IS A DUPLICATE
            )
        ]

def test_normalize_url():
    assert normalize_url("https://example.com/path?utm=123") == "https://example.com/path"
    assert normalize_url("http://example.com/") == "http://example.com"

def test_ecom_filtering():
    # Test that E-Commerce sites are strictly blocked
    amazon_result = SearchResult(url="https://amazon.com/123", title="A", snippet="A", domain="amazon.com")
    flipkart_result = SearchResult(url="https://flipkart.com/123", title="A", snippet="A", domain="flipkart.com")
    alibaba_result = SearchResult(url="https://alibaba.com/123", title="A", snippet="A", domain="alibaba.com")
    valid_result = SearchResult(url="https://freudtools.com/123", title="B", snippet="B", domain="freudtools.com")
    
    assert filter_result(amazon_result) is False
    assert filter_result(flipkart_result) is False
    assert filter_result(alibaba_result) is False
    assert filter_result(valid_result) is True

def test_check_exact_mpn():
    assert check_exact_mpn("123", "Product 123 Specs") is True
    assert check_exact_mpn("123", "Product 81239 Specs") is False
    assert check_exact_mpn("ABC-456", "Buy ABC-456 here") is True

def test_classify_source():
    assert classify_source("https://3m.com/file.pdf", "3m.com", "3m.com") == "manufacturer_document"
    assert classify_source("https://3m.com/product", "3m.com", "3m.com") == "manufacturer_product_page"
    assert classify_source("https://grainger.com/item", "grainger.com", "3m.com") == "distributor"

def test_discover_sources_pipeline(tmp_path):
    plan = SearchPlan(
        product_type="Sanding Belt",
        category_hypothesis="Abrasives",
        attributes_to_find=["Size"],
        search_queries=["Freud Inc DCB518ASTS06G"]
    )
    
    profile = ProductProfile(
        mpn="DCB518ASTS06G",
        manufacturer_canonical="Freud Inc",
        search_plan=plan
    )
    
    mock_client = MockSearchClient()
    result = discover_sources(profile, search_client=mock_client)
    
    # 1. Assert result structure
    assert isinstance(result, SourceDiscoveryResult)
    assert result.status == "success"
    
    # 2. Assert Filtering and Deduplication
    # The mock sent 4 items:
    # - 1 valid PDF
    # - 1 Amazon link (Should be BLOCKED)
    # - 1 Flipkart link (Should be BLOCKED)
    # - 1 duplicate PDF (Should be DEDUPLICATED)
    # So we should be left with exactly 1 source!
    assert len(result.sources) == 1
    
    # 3. Assert the single remaining source is the valid PDF
    top_source = result.sources[0]
    assert top_source.domain == "freudtools.com"
    assert top_source.source_type == "manufacturer_document"

def test_no_acceptable_sources():
    class AllEcomClient:
        def search(self, query: str, max_results: int = 5):
            return [
                SearchResult(url="https://amazon.com/dp/B00123", title="Amazon", snippet="Buy DCB5", domain="amazon.com")
            ]
            
    plan = SearchPlan(
        product_type="Sanding Belt", category_hypothesis="A", attributes_to_find=[], search_queries=["Query"]
    )
    profile = ProductProfile(mpn="DCB5", manufacturer_canonical="Freud", search_plan=plan)
    
    result = discover_sources(profile, search_client=AllEcomClient())
    assert result.status == "no_acceptable_sources"
    assert len(result.sources) == 0
