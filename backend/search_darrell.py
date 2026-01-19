"""Search for Darrell Buttigieg and save to memory"""
import json
import os
from datetime import datetime
import requests

def search_duckduckgo(query, max_results=10):
    """Search using DuckDuckGo HTML interface"""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = {"q": query}
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        # Parse results from HTML
        from html.parser import HTMLParser
        
        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.current = {}
                self.in_result = False
                self.in_title = False
                self.in_snippet = False
                
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and "result__a" in attrs.get("class", ""):
                    self.in_title = True
                    self.current["url"] = attrs.get("href", "")
                if tag == "a" and "result__snippet" in attrs.get("class", ""):
                    self.in_snippet = True
                    
            def handle_endtag(self, tag):
                if tag == "a" and self.in_title:
                    self.in_title = False
                if tag == "a" and self.in_snippet:
                    self.in_snippet = False
                    if self.current.get("title") or self.current.get("snippet"):
                        self.results.append(self.current)
                        self.current = {}
                    
            def handle_data(self, data):
                if self.in_title:
                    self.current["title"] = self.current.get("title", "") + data.strip()
                if self.in_snippet:
                    self.current["snippet"] = self.current.get("snippet", "") + data.strip()
        
        parser = DDGParser()
        parser.feed(response.text)
        return parser.results[:max_results]
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

try:
    print("🔍 Searching for Darrell Buttigieg...")
    
    results = search_duckduckgo("Darrell Buttigieg", max_results=15)
    
    print(f"\n📊 Found {len(results)} results:\n")
    
    collected_info = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        body = r.get("snippet", "")
        url = r.get("url", "")
        print(f"{i}. {title}")
        print(f"   {body[:200]}...")
        print(f"   URL: {url}")
        print()
        collected_info.append({
            "title": title,
            "snippet": body,
            "url": url
        })
    
    # Save to memory
    MEMORY_FILE = os.path.join(os.path.dirname(__file__), "data", "memory", "agent_memory.json")
    
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory = json.load(f)
    else:
        memory = {"knowledge_base": {"facts": []}}
    
    # Add search results as facts
    search_summary = f"Web search about Darrell Buttigieg on {datetime.now().strftime('%Y-%m-%d')}: Found {len(results)} results including: " + "; ".join([r.get("title", "")[:50] for r in results[:5]])
    
    new_facts = [
        {
            "topic": "owner_web_presence",
            "fact": search_summary,
            "confidence": 0.8,
            "source": "web_search_duckduckgo",
            "learned_date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # Add individual findings
    for r in results[:5]:
        new_facts.append({
            "topic": "owner_online_info",
            "fact": f"{r.get('title', '')}: {r.get('body', '')[:100]}",
            "confidence": 0.7,
            "source": r.get("href", "web_search"),
            "learned_date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat()
        })
    
    # Add to memory
    if "knowledge_base" not in memory:
        memory["knowledge_base"] = {"facts": []}
    
    memory["knowledge_base"]["facts"].extend(new_facts)
    memory["last_updated"] = datetime.now().isoformat()
    
    # Save
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Added {len(new_facts)} facts to agent memory!")
    print(f"📁 Saved to: {MEMORY_FILE}")
    
    # Also update user profile with web presence info
    PROFILE_FILE = os.path.join(os.path.dirname(__file__), "data", "forms_db", "user_profiles.json")
    
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        # Add web presence section
        if "profiles" in profiles and "default" in profiles["profiles"]:
            if "web_presence" not in profiles["profiles"]["default"]:
                profiles["profiles"]["default"]["web_presence"] = {}
            
            profiles["profiles"]["default"]["web_presence"]["search_results"] = collected_info[:5]
            profiles["profiles"]["default"]["web_presence"]["last_searched"] = datetime.now().isoformat()
            
            with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Updated user profile with web presence info!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
