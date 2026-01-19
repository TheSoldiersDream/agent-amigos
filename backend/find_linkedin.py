"""Find LinkedIn profile for a person using multiple search engines"""
import requests
import re
from urllib.parse import unquote, quote

def find_linkedin(name):
    print(f"🔍 Searching for LinkedIn profile: {name}")
    print("=" * 50)
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    all_links = []
    
    # Try Bing
    print("\n📍 Trying Bing...")
    try:
        query = f'site:linkedin.com/in {name}'
        url = f'https://www.bing.com/search?q={quote(query)}'
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        # Find LinkedIn URLs
        pattern = r'href=["\']?(https?://[^"\'>\s]*linkedin\.com/in/[^"\'>\s]*)'
        links = re.findall(pattern, response.text, re.IGNORECASE)
        for link in links:
            clean = link.split('&')[0].split('?')[0]
            if clean not in all_links:
                all_links.append(clean)
        print(f"   Found: {len(links)} links")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try DuckDuckGo HTML
    print("\n📍 Trying DuckDuckGo...")
    try:
        query = f'site:linkedin.com {name}'
        url = 'https://html.duckduckgo.com/html/'
        response = requests.post(url, data={'q': query}, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        # Extract from redirect links
        pattern = r'uddg=([^&"\s]+)'
        for match in re.findall(pattern, response.text):
            decoded = unquote(match)
            if 'linkedin.com/in/' in decoded.lower():
                clean = decoded.split('&')[0].split('?')[0]
                if clean not in all_links:
                    all_links.append(clean)
        print(f"   Total now: {len(all_links)} links")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Try Startpage (privacy search)
    print("\n📍 Trying Startpage...")
    try:
        query = f'linkedin.com/in {name}'
        url = f'https://www.startpage.com/sp/search?query={quote(query)}'
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        pattern = r'https?://[^"\'>\s]*linkedin\.com/in/[^"\'>\s&]*'
        links = re.findall(pattern, response.text, re.IGNORECASE)
        for link in links:
            clean = link.split('&')[0].split('?')[0]
            if clean not in all_links and 'linkedin.com/in/' in clean:
                all_links.append(clean)
        print(f"   Total now: {len(all_links)} links")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Display results
    print(f"\n{'='*50}")
    print(f"📋 Found {len(all_links)} LinkedIn profile URLs:")
    
    results = []
    for i, link in enumerate(all_links[:10], 1):
        print(f"   {i}. {link}")
        results.append(link)
    
    # Filter for best match
    name_parts = name.lower().split()
    best_matches = []
    for link in results:
        link_lower = link.lower()
        if any(part in link_lower for part in name_parts):
            best_matches.append(link)
    
    if best_matches:
        print(f"\n✅ Best match for '{name}':")
        print(f"   → {best_matches[0]}")
        return best_matches[0]
    
    return results[0] if results else None

if __name__ == "__main__":
    result = find_linkedin("Darrell Buttigieg")
    if result:
        print(f"\n📋 LinkedIn URL: {result}")
        
        # Save to user profile
        import json
        import os
        profile_path = os.path.join(os.path.dirname(__file__), "data", "forms_db", "user_profiles.json")
        
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
            
            profiles["profiles"]["default"]["social"]["linkedin"] = result
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved LinkedIn URL to user profile!")
