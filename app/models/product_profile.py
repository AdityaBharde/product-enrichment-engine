from pydantic import BaseModel
from typing import Optional, List

class SearchPlan(BaseModel):
    
    product_type: str
    category_hypothesis: str
    attributes_to_find: List[str]
    search_queries: List[str]

class ProductProfile(BaseModel):
    mpn: str
    manufacturer_raw: Optional[str] = None
    manufacturer_canonical: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    department: Optional[str] = None
    search_plan: Optional[SearchPlan] = None