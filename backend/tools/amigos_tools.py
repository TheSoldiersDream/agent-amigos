
import os
import logging
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)

class AmigosTool:
    """
    Amigos Integration for autonomous web agent capabilities.
    Enables bypassing anti-bot measures and performing multi-step web tasks.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AMIGOS_API_KEY")
        # Normalize empty/placeholder keys so callers can reliably check truthiness.
        if self.api_key is not None:
            self.api_key = str(self.api_key).strip()
        if not self.api_key or (self.api_key.startswith("${") and self.api_key.endswith("}")):
            self.api_key = None
        self.base_url = os.environ.get("AMIGOS_API_BASE", "http://127.0.0.1:65252")
        self.execute_url = f"{self.base_url}/scrape/dynamic"

        # Avoid indefinite hangs: requests timeout defaults to None.
        # Allow override via env (seconds).
        try:
            self.timeout_s = float(os.environ.get("AMIGOS_TIMEOUT", "60"))
        except Exception:
            self.timeout_s = 60.0
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def _unwrap_json_payload(obj: Any) -> Any:
        """Best-effort normalize of Amigos response shapes.

        Some endpoints may return nested payloads like {"data": {...}}.
        This keeps the tool resilient without hard-coding a single schema.
        """
        if isinstance(obj, dict) and isinstance(obj.get("data"), dict):
            return obj.get("data")
        return obj

    def execute(self, task: str, urls: Optional[List[str]] = None, input_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a task using the web agent.
        """
        if not self.api_key:
            return {"success": False, "error": "AMIGOS_API_KEY not set"}
            
        payload: Dict[str, Any] = {"task": task}
        if urls: payload["urls"] = urls
        if input_data: payload["input"] = input_data
        
        try:
            response = requests.post(
                self.execute_url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            try:
                data = self._unwrap_json_payload(response.json())
            except Exception as e:
                return {"success": False, "error": f"Amigos returned non-JSON response: {e}"}
            return {"success": True, "data": data}
        except requests.exceptions.Timeout as e:
            logger.error(f"Amigos Execute timeout: {e}")
            return {"success": False, "error": "Amigos request timed out"}
        except Exception as e:
            logger.error(f"Amigos Execute error: {e}")
            return {"success": False, "error": str(e)}

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        High-quality scraping that handles JS rendering and bypasses blocks.
        """
        if not self.api_key:
            return {"success": False, "error": "AMIGOS_API_KEY not set"}
            
        try:
            response = requests.post(
                f"{self.base_url}/scrape",
                headers=self._get_headers(),
                json={"url": url},
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            try:
                data = self._unwrap_json_payload(response.json())
            except Exception as e:
                return {"success": False, "error": f"Amigos returned non-JSON response: {e}"}
            return {"success": True, "data": data}
        except requests.exceptions.Timeout as e:
            logger.error(f"Amigos Scrape timeout: {e}")
            return {"success": False, "error": "Amigos request timed out"}
        except Exception as e:
            logger.error(f"Amigos Scrape error: {e}")
            return {"success": False, "error": str(e)}

    def agent_task(self, prompt: str, url: Optional[str] = None, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Autonomous multi-step retrieval. 
        Example prompt: 'Find the current odds for the first 3 races at Randwick'
        """
        if not self.api_key:
            return {"success": False, "error": "AMIGOS_API_KEY not set"}
            
        payload: Dict[str, Any] = {"input": prompt}
        if url: payload["url"] = url
        if schema: payload["schema"] = schema
        
        try:
            response = requests.post(
                f"{self.base_url}/agent",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            try:
                data = self._unwrap_json_payload(response.json())
            except Exception as e:
                return {"success": False, "error": f"Amigos returned non-JSON response: {e}"}
            return {"success": True, "data": data}
        except requests.exceptions.Timeout as e:
            logger.error(f"Amigos Agent task timeout: {e}")
            return {"success": False, "error": "Amigos request timed out"}
        except Exception as e:
            logger.error(f"Amigos Agent task error: {e}")
            return {"success": False, "error": str(e)}

    def vibe_scrape(self, prompt: str, url: str) -> Dict[str, Any]:
        """
        Extract structured data from a specific page using natural language description.
        """
        return self.agent_task(prompt=f"Extract this data from the page: {prompt}", url=url)

# Singleton instance
amigos = AmigosTool()

def amigos_agent(prompt: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Autonomous web agent call for Agent Amigos."""
    return amigos.agent_task(prompt, url)

def amigos_scrape(url: str) -> Dict[str, Any]:
    """High-quality web scraping call for Agent Amigos."""
    return amigos.scrape(url)
