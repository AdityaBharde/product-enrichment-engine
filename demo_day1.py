import pandas as pd
import json
import os
from app.services.profiler import profile_csv
from app.services.schema_mapper import generate_mapping_report, convert_to_canonical
from app.services.product_analyzer import analyze_product

def run_demo():
    # Make sure this points to your actual 1000-row CSV
    csv_path = os.path.join("data", "raw", "input.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}. Please make sure your UniHack CSV is there!")
        return

    print("==================================================")
    print("🚀 FORGEIQ DAY 1 PIPELINE DEMO")
    print("==================================================\n")

    # ---------------------------------------------------------
    # STEP 1: Profiler
    # ---------------------------------------------------------
    print("➡️ STEP 1: Profiling the CSV...")
    profile_data, profile_path = profile_csv(csv_path)
    print(f"✅ Profile complete! Saved to {profile_path}")
    print(f"   Detected {profile_data['dataset']['rows']} rows and {profile_data['dataset']['column_count']} columns.")
    print(f"   Suspicious columns found: {len(profile_data['suspicious_columns'])}\n")

    # ---------------------------------------------------------
    # STEP 2: Schema Mapper
    # ---------------------------------------------------------
    print("➡️ STEP 2: Intelligently Mapping Columns...")
    df = pd.read_csv(csv_path)
    columns = df.columns.tolist()
    mapping_report, mapping_path = generate_mapping_report(columns, csv_path)
    print(f"✅ Mapping complete! Saved to {mapping_path}")
    print("   Internal Mapping Engine Decision:")
    print(json.dumps(mapping_report["mapping"], indent=4))
    print("\n")

    # ---------------------------------------------------------
    # STEP 3 & 4: Process Multiple Rows
    # ---------------------------------------------------------
    # CHANGE: We now grab the first 3 rows instead of 1
    demo_count = 10
    print(f"➡️ STEP 3 & 4: Extracting and Analyzing Top {demo_count} Rows...\n")
    
    df_sample = df.head(demo_count) 
    canonical_records = convert_to_canonical(df_sample, mapping_report["mapping"])
    
    # Loop through the 3 records and analyze each one
    for index, record in enumerate(canonical_records, start=1):
        print(f"--- PROCESSING PRODUCT #{index} ---")
        
        # Run the Product Analyzer
        product_profile = analyze_product(record)
        
        print("✅ Final Product Profile & Search Plan:")
        print(product_profile.model_dump_json(indent=4))
        print("\n" + "-"*50 + "\n")

    print("==================================================")
    print("🏁 DAY 1 PIPELINE DEMO COMPLETE!")
    print("==================================================")

if __name__ == "__main__":
    run_demo()