import os
import json
import pandas as pd
from app.services.schema_mapper import (
    map_columns, 
    generate_mapping_report, 
    convert_to_canonical
)

def test_map_columns_exact_and_alias():
    columns = ["SKU", "Product_Title", "Maker", "Brand", "Random_Notes"]
    mapping = map_columns(columns)
    
    assert mapping["SKU"] == "part_number"
    assert mapping["Product_Title"] == "description"
    assert mapping["Maker"] == "manufacturer"
    assert mapping["Brand"] == "brand"
    assert mapping["Random_Notes"] == "unmapped"

def test_map_columns_fuzzy_and_multi_brand():
    # "Mfg_Part_Num" is an exact alias match.
    # "prt_desc" should fuzzy match "part_desc" -> description.
    # We have multiple brands.
    columns = ["Mfg_Part_Num", "prt_desc", "E1_Brand", "Unilog_Brand", "DIB_Brand"]
    mapping = map_columns(columns)
    
    assert mapping["Mfg_Part_Num"] == "part_number"
    assert mapping["prt_desc"] == "description"
    assert mapping["E1_Brand"] == "brand"
    assert mapping["Unilog_Brand"] == "brand"
    assert mapping["DIB_Brand"] == "brand"

def test_ambiguity_prevention():
    # If multiple columns could be SKU, first one wins to prevent overwriting.
    columns = ["sku", "item_code", "product_title"]
    mapping = map_columns(columns)
    
    assert mapping["sku"] == "part_number"
    assert mapping["item_code"] == "unmapped"  
    assert mapping["product_title"] == "description" 

def test_generate_mapping_report(tmp_path):
    test_csv_path = tmp_path / "test_data.csv"
    columns = ["SKU", "Product_Title"]
    
    report, report_path = generate_mapping_report(columns, str(test_csv_path))
    
    assert os.path.exists(report_path)
    assert report["canonical_fields_found"] == ["description", "part_number"] or report["canonical_fields_found"] == ["part_number", "description"]
    assert report["unmapped_fields"] == []

def test_convert_to_canonical():
    # Simulate a loaded dataframe
    data = [
        {"sku": "123", "title": "Hammer", "maker": "Stanley", "e1_brand": "STAN", "notes": "sale"}
    ]
    df = pd.DataFrame(data)
    
    mapping = {
        "sku": "part_number",
        "title": "description",
        "maker": "manufacturer",
        "e1_brand": "brand",
        "notes": "unmapped"
    }
    
    records = convert_to_canonical(df, mapping)
    
    assert len(records) == 1
    assert records[0].part_number == "123"
    assert records[0].description == "Hammer"
    assert records[0].manufacturer == "Stanley"
    assert records[0].brands == ["STAN"]
    assert records[0].unmapped_data == {"notes": "sale"}