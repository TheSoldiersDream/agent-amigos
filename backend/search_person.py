"""
Search for a person online using multi-provider search (Google/Bing/Brave fallback)
Saves results to agent memory and user profile
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.web_tools import WebTools

def search_person(name: str = "Darrell Buttigieg", max_results: int = 10):
    """Search for a person and save findings to memory"""
    print(f"🔍 Searching for information about {name}...")
    print("=" * 60)
    print("Providers: Google → Brave → DuckDuckGo → Bing (auto-fallback)")
    print("=" * 60)
    
    web = WebTools()
    
    # Search with auto-fallback between providers
    result = web.web_search(name, max_results=max_results, provider="auto")
    
    if not result["success"]:
        print(f"\n❌ Search failed: {result.get('error', 'Unknown error')}")
        return None
    
    provider = result.get("provider", "unknown")
    results = result["results"]
    
    print(f"\n✅ Search successful! (Provider: {provider})")
    print(f"Found {len(results)} results:\n")
    
    collected_info = []
    for i, item in enumerate(results, 1):
        title = item.get('title', 'No title')
        url = item.get('href', item.get('url', 'No URL'))
        body = item.get('body', item.get('snippet', ''))
        
        print(f"{i}. {title}")
        print(f"   URL: {url}")
        if body:
            print(f"   {body[:200]}...")
        print()
        
        collected_info.append({
            "title": title,
            "url": url,
            "snippet": body[:300] if body else ""
        })
    
    # Save to agent memory
    save_to_memory(name, collected_info, provider)
    
    # Save to user profile
    save_to_profile(name, collected_info)
    
    return collected_info

def save_to_memory(name: str, results: list, provider: str):
    """Save search results to agent memory"""
    memory_path = os.path.join(os.path.dirname(__file__), "data", "memory", "agent_memory.json")
    
    try:
        memory = {"facts": [], "preferences": [], "knowledge_base": {"facts": []}}
        if os.path.exists(memory_path):
            with open(memory_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
        
        # Create summary
        search_summary = f"Web search for '{name}' on {datetime.now().strftime('%Y-%m-%d %H:%M')} via {provider}: Found {len(results)} results"
        
        # Add main search fact
        fact = {
            "topic": name.lower().replace(" ", "_"),
            "fact": search_summary,
            "confidence": 0.8,
            "source": f"web_search_{provider}",
            "learned_date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "details": [r["title"] for r in results[:5]]
        }
        
        # Ensure knowledge_base exists
        if "knowledge_base" not in memory:
            memory["knowledge_base"] = {"facts": []}
        if "facts" not in memory["knowledge_base"]:
            memory["knowledge_base"]["facts"] = []
        
        memory["knowledge_base"]["facts"].append(fact)
        
        # Add individual results as facts
        for r in results[:5]:
            memory["knowledge_base"]["facts"].append({
                "topic": f"{name.lower().replace(' ', '_')}_online",
                "fact": f"{r['title']}: {r['snippet'][:100]}" if r['snippet'] else r['title'],
                "confidence": 0.7,
                "source": r['url'],
                "learned_date": datetime.now().strftime("%Y-%m-%d")
            })
        
        memory["last_updated"] = datetime.now().isoformat()
        
        # Save
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(results[:5]) + 1} facts to agent memory!")
        print(f"   📁 {memory_path}")
        
    except Exception as e:
        print(f"⚠️ Could not save to memory: {e}")

def save_to_profile(name: str, results: list):
    """Save search results to user profile"""
    profile_path = os.path.join(os.path.dirname(__file__), "data", "forms_db", "user_profiles.json")
    
    try:
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
            
            if "profiles" in profiles and "default" in profiles["profiles"]:
                if "web_presence" not in profiles["profiles"]["default"]:
                    profiles["profiles"]["default"]["web_presence"] = {}
                
                profiles["profiles"]["default"]["web_presence"]["search_results"] = results[:5]
                profiles["profiles"]["default"]["web_presence"]["last_searched"] = datetime.now().isoformat()
                profiles["profiles"]["default"]["web_presence"]["search_name"] = name
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profiles, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Updated user profile with web presence info!")
    except Exception as e:
        print(f"⚠️ Could not update profile: {e}")

if __name__ == "__main__":
    # Default search or use command line argument
    name = sys.argv[1] if len(sys.argv) > 1 else "Darrell Buttigieg"
    search_person(name)
