import argparse
import json
import os
import pandas as pd
from pydantic import BaseModel
from typing import Optional, List

class OutputFieldDefinition(BaseModel):
    name: str
    source: str
    data_type: str
    required: bool
    generation_method: str
    description: Optional[str] = None
    max_length: Optional[int] = None

class OutputSchemaRegistry(BaseModel):
    version: str
    total_columns: int
    columns: List[OutputFieldDefinition]

def classify_column(col_name: str) -> OutputFieldDefinition:
   
    col_upper = col_name.upper()
    
    # Defaults for unrecognized columns
    source = "unknown"
    data_type = "string"
    required = False
    generation_method = "not_implemented"
    max_length = None
    
    # 1. Identity / classification
    if col_upper in ["MANUFACTURER_NAME", "BRAND_NAME"]:
        source = "entity_resolution"
        required = True
        generation_method = "entity_resolution"
    elif col_upper in ["MANUFACTURER_PART_NUMBER", "MFG_PART_NUM", "MPN"]:
        source = "input"
        required = True
        generation_method = "input_passthrough"
    elif "CLASS" in col_upper or "DEPARTMENT" in col_upper or "CATEGORY" in col_upper:
        source = "classification"
        generation_method = "classification"
        
    # 2. Content / descriptions
    elif "DESC" in col_upper or "MARKETING" in col_upper:
        source = "content_generation"
        generation_method = "llm_generation_from_verified_facts"
        if "MOBILE" in col_upper:
            max_length = 80
        elif "INVOICE" in col_upper:
            max_length = 40
            
    # 3. Attributes
    elif "ATTRIBUTE" in col_upper:
        source = "verified_attribute"
        if "LABEL" in col_upper or "VALUE" in col_upper:
            generation_method = "attribute_extraction"
        elif "UOM" in col_upper:
            generation_method = "normalization"
            
    # 4. Features
    elif "FEATURE" in col_upper or "BULLET" in col_upper:
        source = "evidence"
        generation_method = "evidence_backed_extraction"
        
    # 5. Dimensions
    elif any(dim in col_upper for dim in ["LENGTH", "WIDTH", "HEIGHT", "DEPTH", "WEIGHT", "VOLUME", "DIMENSION"]):
        source = "dimensions"
        generation_method = "normalization"
        if "VALUE" in col_upper:
            data_type = "float"
            
    # 6. Commerce identifiers
    elif col_upper in ["UPC", "EAN", "GTIN", "ASIN"]:
        source = "commerce_identifiers"
        generation_method = "source_retrieval"
        
    # 7. References / digital assets
    elif "URL" in col_upper or "IMAGE" in col_upper or "DOCUMENT" in col_upper or "PDF" in col_upper or "ASSET" in col_upper:
        source = "digital_assets"
        generation_method = "source_discovery"
        data_type = "url"
        
    return OutputFieldDefinition(
        name=col_name,
        source=source,
        data_type=data_type,
        required=required,
        generation_method=generation_method,
        max_length=max_length
    )

def build_schema_registry(csv_path: str, output_path: str) -> OutputSchemaRegistry:
  
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
    # 15. Validation
    with open(csv_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    
    if not first_line:
        raise ValueError("CSV has no columns.")
        
    raw_columns = first_line.split(',')
    if len(set(raw_columns)) != len(raw_columns):
        raise ValueError("CSV contains duplicate column names.")

    # Only load headers (0 rows of data) to extract column names efficiently
    df = pd.read_csv(csv_path, nrows=0)
    columns = df.columns.tolist()

        
    field_definitions = []
    for col in columns:
        field_def = classify_column(col)
        field_definitions.append(field_def)
        
    registry = OutputSchemaRegistry(
        version="1.0",
        total_columns=len(columns),
        columns=field_definitions
    )
    
    # Save the registry to JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(registry.model_dump_json(indent=2))
        
    return registry

def main():
    parser = argparse.ArgumentParser(description="Generate Output Schema Registry from a delivery CSV.")
    parser.add_argument("csv_path", type=str, help="Path to the delivery CSV file.")
    args = parser.parse_args()
    
    output_path = os.path.join("data", "reports", "output_schema_registry.json")
    
    try:
        registry = build_schema_registry(args.csv_path, output_path)
        print("Output schema loaded")
        print(f"Columns detected: {registry.total_columns}")
        print(f"Registry generated: {len(registry.columns)} fields")
        print(f"Saved to: {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
