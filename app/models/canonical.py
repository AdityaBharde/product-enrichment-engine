from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class CanonicalInputRecord(BaseModel):
   
    part_number: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    
    brands: List[str] = []
    
    # Any column that could not be mapped is safely preserved here
    unmapped_data: Dict[str, Any] = {}