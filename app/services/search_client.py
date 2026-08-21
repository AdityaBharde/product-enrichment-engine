import os
import httpx
import urllib.parse
from pydantic import BaseModel
from typing import List

class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    domain: str

class SearchClient:
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        from dotenv import load_dotenv
        load_dotenv()  # Load variables from .env file if it exists
        
        # Do not hardcode API keys. Retrieve from environment.
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ValueError(
                "SERPER_API_KEY environment variable is missing. "
            )
        
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": max_results
        }
        
        results = []
        try:
            # Synchronous HTTP request to the search provider
            response = httpx.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("organic", []):
                link = item.get("link", "")
                # Extract the base domain (e.g., www.amazon.com -> amazon.com)
                parsed_uri = urllib.parse.urlparse(link)
                domain = parsed_uri.netloc.replace("www.", "")
                
                results.append(SearchResult(
                    url=link,
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    domain=domain
                ))
                
        except Exception as e:
            print(f"SearchClient Error executing query '{query}': {e}")
            
        return results