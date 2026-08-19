import os
import json
import pytest
import pandas as pd
from app.services.schema_registry import build_schema_registry, OutputSchemaRegistry

def test_build_schema_registry(tmp_path):
    # 1. Loading the delivery CSV with a temporary test fixture
    test_csv = tmp_path / "test_delivery.csv"
    test_out = tmp_path / "output_schema_registry.json"
    
    # Example exact column names representing various classifications
    columns = [
        "MANUFACTURER_PART_NUMBER",
        "MANUFACTURER_NAME",
        "BRAND_NAME",
        "MOBILE_DESC",
        "INVOICE_DESC",
        "ATTRIBUTE_LABEL_1",
        "ATTRIBUTE_VALUE_1",
        "ATTRIBUTE_UOM_1",
        "ITEM_WEIGHT_VALUE",
        "ITEM_WEIGHT_UOM",
        "PRODUCT_IMAGE_URL_1",
        "UPC",
        "UNKNOWN_COLUMN"
    ]
    
    # Save the synthetic delivery CSV
    df = pd.DataFrame(columns=columns)
    df.to_csv(test_csv, index=False)
    
    # Run the registry builder
    registry = build_schema_registry(str(test_csv), str(test_out))
    
    # 2. Detecting the exact number of columns
    assert isinstance(registry, OutputSchemaRegistry)
    assert registry.total_columns == 13
    assert len(registry.columns) == 13
    
    # 3. Preserving column order
    assert [col.name for col in registry.columns] == columns
    
    # 5. Creating a registry entry for every column
    # Check specific classifications (Playbook logic mapping)
    mpn = registry.columns[0]
    assert mpn.name == "MANUFACTURER_PART_NUMBER"
    assert mpn.source == "input"
    assert mpn.required is True
    assert mpn.generation_method == "input_passthrough"
    
    brand = registry.columns[2]
    assert brand.name == "BRAND_NAME"
    assert brand.source == "entity_resolution"
    
    mobile = registry.columns[3]
    assert mobile.name == "MOBILE_DESC"
    assert mobile.max_length == 80
    assert mobile.generation_method == "llm_generation_from_verified_facts"
    
    attr_val = registry.columns[6]
    assert attr_val.name == "ATTRIBUTE_VALUE_1"
    assert attr_val.source == "verified_attribute"
    assert attr_val.generation_method == "attribute_extraction"
    
    attr_uom = registry.columns[7]
    assert attr_uom.name == "ATTRIBUTE_UOM_1"
    assert attr_uom.source == "verified_attribute"
    assert attr_uom.generation_method == "normalization"

    dim = registry.columns[8]
    assert dim.name == "ITEM_WEIGHT_VALUE"
    assert dim.source == "dimensions"
    assert dim.data_type == "float"
    
    commerce = registry.columns[11]
    assert commerce.name == "UPC"
    assert commerce.source == "commerce_identifiers"

    unknown = registry.columns[-1]
    assert unknown.name == "UNKNOWN_COLUMN"
    assert unknown.source == "unknown"
    
    # 7. Saving/loading the registry JSON
    assert os.path.exists(test_out)
    with open(test_out, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["total_columns"] == 13
    assert len(data["columns"]) == 13
    assert data["columns"][0]["name"] == "MANUFACTURER_PART_NUMBER"

def test_duplicate_columns(tmp_path):
    # 4. Detecting duplicate column names
    test_csv = tmp_path / "dupe_delivery.csv"
    test_out = tmp_path / "dupe_out.json"
    
    with open(test_csv, "w", encoding="utf-8") as f:
        # Intentionally passing COL1 twice
        f.write("COL1,COL1,COL2\n,,")
        
    with pytest.raises(ValueError, match="duplicate column names"):
        build_schema_registry(str(test_csv), str(test_out))

def test_empty_csv(tmp_path):
    # Test handling completely empty file
    test_csv = tmp_path / "empty.csv"
    test_out = tmp_path / "empty_out.json"
    
    with open(test_csv, "w", encoding="utf-8") as f:
        f.write("")
        
    # Our validation logic now throws ValueError before pandas parses it
    with pytest.raises(ValueError, match="CSV has no columns"):
        build_schema_registry(str(test_csv), str(test_out))
