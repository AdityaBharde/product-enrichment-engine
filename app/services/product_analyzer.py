import re
from app.models.canonical import CanonicalInputRecord
from app.models.product_profile import ProductProfile, SearchPlan

# Simple deterministic alias dictionary for Entity Resolution
KNOWN_MANUFACTURERS = {
    "dewlt": "Black & Decker",
    "jamin": "Jam Industrial Supply",
    "2435": "Freud Inc",
    "boica": "Boise Cascade",
    "3m": "3M"
}

def clean_mpn(mpn: str) -> str:
    if not mpn:
        return ""
    # Strip everything except letters, numbers, and dashes
    cleaned = re.sub(r'[^A-Za-z0-9\-]', '', mpn)
    return cleaned.upper()

def normalize_manufacturer(mfg: str) -> str:
    if not mfg:
        return "Unknown"
        
    lower_mfg = mfg.lower().strip()
    
    # Exact/Substring alias matching
    for alias, canonical in KNOWN_MANUFACTURERS.items():
        if alias in lower_mfg:
            return canonical
            
    # Fallback if no alias matches
    return mfg.strip().title()

def extract_brand_clues(brands: list[str], desc: str) -> str:
    # Filter out known placeholders that the mapper might have let through
    valid_brands = [
        b for b in brands 
        if b and b.strip() and "unbranded" not in b.lower() and "no " not in b.lower()
    ]
    
    if valid_brands:
        return valid_brands[0].strip().title()
        
    # If no brand columns exist, try extracting the first word of the description
    if desc:
        return desc.split()[0].upper()
        
    return "Unknown"

def classify_product(desc: str) -> tuple[str, str, list[str]]:
    
    desc_lower = desc.lower() if desc else ""
    
    if "sanding" in desc_lower or "stikit" in desc_lower or "cubitron" in desc_lower:
        return "Abrasive Material", "Abrasives", ["Grit", "Size", "Material", "Pack Quantity"]
        
    if "drill" in desc_lower:
        return "Power Drill", "Power Tools", ["Voltage", "RPM", "Chuck Size", "Torque"]
        
    if "saw" in desc_lower or "blade" in desc_lower:
        return "Saw / Blade", "Cutting Tools", ["Diameter", "Arbor Size", "Teeth Per Inch"]
        
    return "General Item", "General", ["Weight", "Dimensions", "Color"]

def build_search_plan(mpn: str, mfg: str, p_type: str, cat: str, attrs: list[str]) -> SearchPlan:
    
    queries = [
        f'{mfg} {mpn} official product page',
        f'{mfg} {mpn} {p_type} specifications PDF'
    ]
    
    return SearchPlan(
        product_type=p_type,
        category_hypothesis=cat,
        attributes_to_find=attrs,
        search_queries=queries
    )

def analyze_product(record: CanonicalInputRecord) -> ProductProfile:
  
    # 1 & 2: Entity Resolution
    mpn = clean_mpn(record.part_number or "")
    mfg_canon = normalize_manufacturer(record.manufacturer or "")
    
    # 3: Brand Clues
    brand = extract_brand_clues(record.brands, record.description or "")
    
    # 4: Classification
    p_type, cat, attrs = classify_product(record.description or "")
    
    # 5: Search Planner
    plan = build_search_plan(mpn, mfg_canon, p_type, cat, attrs)
    
    # Output the final Evidence Model
    return ProductProfile(
        mpn=mpn,
        manufacturer_raw=record.manufacturer,
        manufacturer_canonical=mfg_canon,
        brand=brand,
        product_type=p_type,
        department=cat,
        search_plan=plan
    )