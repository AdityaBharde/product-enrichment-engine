from app.models.canonical import CanonicalInputRecord
from app.services.product_analyzer import analyze_product

def test_product_analyzer_pipeline():
   
    # 1. Create a raw input record (Simulating Feature 4 output)
    raw_record = CanonicalInputRecord(
        part_number=" 3MABR-7100075678  ",
        description="3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box",
        manufacturer="Jam Industrial Supply LLC (JAMIN)",
        brands=["-- Unbranded --", " "],  # Simulating noisy/placeholder brands
        unmapped_data={}
    )
    
    # 2. Run the Product Analyzer
    profile = analyze_product(raw_record)
    
    # 3. Assert Entity Resolution (clean_mpn, normalize_manufacturer)
    assert profile.mpn == "3MABR-7100075678"
    assert profile.manufacturer_canonical == "Jam Industrial Supply"
    
    # 4. Assert Brand Extraction (fallback to description if placeholders exist)
    assert profile.brand == "3M"
    
    # 5. Assert Classification
    assert profile.product_type == "Abrasive Material"
    assert profile.department == "Abrasives"
    
    # 6. Assert Search Planner
    plan = profile.search_plan
    assert plan is not None
    assert "Grit" in plan.attributes_to_find
    assert len(plan.search_queries) == 2
    assert '"Jam Industrial Supply" "3MABR-7100075678"' in plan.search_queries[0]