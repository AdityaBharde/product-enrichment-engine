import json
import os
import difflib
import pandas as pd
from app.models.canonical import CanonicalInputRecord

ALIASES = {
    "part_number": ["sku", "mpn", "part_num", "mfg_part_num", "item_code", "part_number", "id"],
    "description": ["desc", "title", "name", "product_title", "part_desc", "product_name"],
    "manufacturer": ["mfg", "maker", "manufacturer", "part_manuf", "supplier", "vendor"],
    "brand": ["brand", "e1_brand", "unilog_brand", "dib_brand"]
}

def normalize_name(col: str) -> str:
    return "".join(c if c.isalnum() else " " for c in col).lower().strip()

def map_columns(columns: list[str]) -> dict:
    
    mapping = {}
    used_targets = set()
    brand_cols = []

    for col in columns:
        norm_col = normalize_name(col)
        matched = False
        
        # 1. Exact alias match
        for target, aliases in ALIASES.items():
            norm_aliases = [normalize_name(a) for a in aliases]
            
            # Check exact match against the target name or its aliases
            if norm_col in norm_aliases or norm_col == target:
                if target == "brand":
                    brand_cols.append(col)
                    matched = True
                    break
                elif target not in used_targets:
                    # Ambiguity detection: For non-brand fields, first match wins.
                    # Prevents overriding part_number if multiple SKU columns exist.
                    mapping[col] = target
                    used_targets.add(target)
                    matched = True
                    break
        
        if matched:
            continue
            
        # 2. Fuzzy match
        for target, aliases in ALIASES.items():
            if target != "brand" and target in used_targets:
                continue
                
            norm_aliases = [normalize_name(a) for a in aliases]
            # Use Python's built-in difflib for fuzzy matching (80% similarity threshold)
            matches = difflib.get_close_matches(norm_col, norm_aliases, n=1, cutoff=0.8)
            
            if matches:
                if target == "brand":
                    brand_cols.append(col)
                else:
                    mapping[col] = target
                    used_targets.add(target)
                matched = True
                break
                
        # 3. Unmapped column preservation
        if not matched:
            mapping[col] = "unmapped"

    # Assign all discovered brand columns
    for b in brand_cols:
        mapping[b] = "brand"

    return mapping

def generate_mapping_report(columns: list[str], file_path: str) -> tuple[dict, str]:
   
    mapping = map_columns(columns)
    
    report = {
        "version": "1.0",
        "original_columns": columns,
        "mapping": mapping,
        "canonical_fields_found": list(set([v for v in mapping.values() if v not in ("unmapped", "brand")])),
        "brand_fields_found": [k for k, v in mapping.items() if v == "brand"],
        "unmapped_fields": [k for k, v in mapping.items() if v == "unmapped"]
    }
    
    reports_dir = os.path.join("data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    report_path = os.path.join(reports_dir, f"{base_name}_input_mapping.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report, report_path

def convert_to_canonical(df: pd.DataFrame, mapping: dict) -> list[CanonicalInputRecord]:
 
    records = []
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        
        part_number = None
        description = None
        manufacturer = None
        brands = []
        unmapped_data = {}
        
        for orig_col, target in mapping.items():
            val = row_dict.get(orig_col)
            
            # Safely handle pandas NaNs and format strings
            if pd.isna(val):
                val = None
            elif isinstance(val, str):
                val = val.strip()
                if val == "":
                    val = None
                
            if target == "part_number":
                part_number = str(val) if val is not None else None
            elif target == "description":
                description = str(val) if val is not None else None
            elif target == "manufacturer":
                manufacturer = str(val) if val is not None else None
            elif target == "brand":
                if val:
                    brands.append(str(val))
            else:
                unmapped_data[orig_col] = val
                
        records.append(CanonicalInputRecord(
            part_number=part_number,
            description=description,
            manufacturer=manufacturer,
            brands=brands,
            unmapped_data=unmapped_data
        ))
        
    return records