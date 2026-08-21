import pandas as pd
import json
import os
from app.services.profiler import profile_csv
from app.services.schema_mapper import generate_mapping_report, convert_to_canonical
from app.services.product_analyzer import analyze_product
from app.services.source_discovery import discover_sources

def run_demo():
    # Point to the real UniHack dataset
    csv_path = os.path.join("data", "raw", "input.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}.")
        return
        
    print("==================================================")
    print("FORGEIQ LIVE WEB DISCOVERY DEMO (DAY 2)")
    print("==================================================\n")

    # ---------------------------------------------------------
    # 1. Day 1 Pipeline (Fast Forward)
    # ---------------------------------------------------------
    print("Processing Row #1 through Day 1 Pipeline...")
    df = pd.read_csv(csv_path)
    mapping_report, _ = generate_mapping_report(df.columns.tolist(), csv_path)
    
    # Grab just the first row
    df_sample = df.head(1)
    canonical_records = convert_to_canonical(df_sample, mapping_report["mapping"])
    product_profile = analyze_product(canonical_records[0])
    
    print(f"Product Identified: {product_profile.manufacturer_canonical} | {product_profile.mpn}")
    print(f"Executing these queries on Google via Serper:")
    for q in product_profile.search_plan.search_queries:
        print(f"   - {q}")
    
    # ---------------------------------------------------------
    # 2. Day 2 Feature 1 (Live Source Discovery)
    # ---------------------------------------------------------
    print("\nSearching the web & enforcing E-Commerce blocklist...")
    
    try:
        discovery_result = discover_sources(product_profile)
    except ValueError as e:
        print(f"\nAPI KEY ERROR: {e}")
        print("Please make sure you ran: $env:SERPER_API_KEY=\"your_key_here\"")
        return
    
    if discovery_result.status == "no_acceptable_sources":
        print("\nNo acceptable non-e-commerce sources were found for this product.")
        return
        
    print(f"\nSuccess! Filtered down to {len(discovery_result.sources)} highly authoritative sources.\n")
    
    print("TOP RANKED SOURCES:")
    for source in discovery_result.sources:
        print(f"[{source.rank}] {source.domain} ({source.source_type})")
        print(f"    URL: {source.url}")
        print(f"    Title: {source.title}")
        print(f"    Authority: {source.authority_score} | Relevance: {source.relevance_score:.2f}")
        print(f"    Exact MPN Match: {source.exact_mpn_match}")
        print("-" * 60)
        
    print(f"\nFull JSON saved to: data/processed/source_discovery/{product_profile.mpn}.json")

if __name__ == "__main__":
    run_demo()
