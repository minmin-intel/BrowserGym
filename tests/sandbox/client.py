#!/usr/bin/env python3
"""
Example client for the Playwright browser sandbox API.
"""

import argparse
import json
import requests
import sys
import time
from typing import Dict, Optional

class PlaywrightClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.browser_id = None
        self.context_id = None
        self.page_id = None
    
    def launch_browser(self, headless: bool = True) -> Dict:
        """Launch a new browser instance."""
        response = requests.post(
            f"{self.base_url}/browser/launch",
            json={"headless": headless}
        )
        data = response.json()
        self.browser_id = data.get("browser_id")
        return data
    
    def create_context(self, width: int = 1280, height: int = 720) -> Dict:
        """Create a new browser context."""
        if not self.browser_id:
            raise ValueError("Browser not launched yet")
        
        response = requests.post(
            f"{self.base_url}/browser/{self.browser_id}/context",
            json={"width": width, "height": height}
        )
        data = response.json()
        self.context_id = data.get("context_id")
        return data
    
    def create_page(self) -> Dict:
        """Create a new page."""
        if not self.context_id:
            raise ValueError("Context not created yet")
        
        response = requests.post(
            f"{self.base_url}/context/{self.context_id}/page",
        )
        data = response.json()
        self.page_id = data.get("page_id")
        return data
    
    def navigate(self, url: str, wait_until: str = "networkidle") -> Dict:
        """Navigate to a URL."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/navigate",
            json={"url": url, "wait_until": wait_until}
        )
        return response.json()
    
    def click(self, selector: str) -> Dict:
        """Click on an element matching the selector."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/click",
            json={"selector": selector}
        )
        return response.json()
    
    def type_text(self, selector: str, text: str) -> Dict:
        """Type text into an element matching the selector."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/type",
            json={"selector": selector, "text": text}
        )
        return response.json()
    
    def evaluate(self, expression: str) -> Dict:
        """Evaluate JavaScript in the page context."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/evaluate",
            json={"expression": expression}
        )
        return response.json()
    
    def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> Dict:
        """Take a screenshot of the page."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/screenshot",
            json={"path": path, "full_page": full_page}
        )
        return response.json()
    
    def cleanup(self) -> None:
        """Close all resources."""
        if self.page_id:
            requests.post(f"{self.base_url}/page/{self.page_id}/close")
        
        if self.context_id:
            requests.post(f"{self.base_url}/context/{self.context_id}/close")
        
        if self.browser_id:
            requests.post(f"{self.base_url}/browser/{self.browser_id}/close")


def main():
    parser = argparse.ArgumentParser(description="Example client for Playwright browser sandbox API")
    parser.add_argument("--url", type=str, default="https://www.google.com", help="URL to navigate to")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="API server URL")
    
    args = parser.parse_args()
    
    client = PlaywrightClient(base_url=args.server)
    
    try:
        print("Launching browser...")
        client.launch_browser(headless=args.headless)
        
        print("Creating context...")
        client.create_context()
        
        print("Creating page...")
        client.create_page()
        
        print(f"Navigating to {args.url}...")
        client.navigate(args.url)
        
        print("Taking screenshot...")
        screenshot_result = client.screenshot(path="screenshot.png")
        print(f"Screenshot saved: {screenshot_result}")
        
        # Example of evaluating JavaScript
        print("Getting page title...")
        title_result = client.evaluate("document.title")
        print(f"Page title: {title_result.get('result', '')}")
        
        # Wait a bit to see the browser if running in non-headless mode
        if not args.headless:
            print("Waiting for 3 seconds...")
            time.sleep(3)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        print("Cleaning up resources...")
        client.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
