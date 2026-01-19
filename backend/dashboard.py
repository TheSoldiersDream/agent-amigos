"""
Real-time Agent Amigos Health Dashboard
Run this to see live system stats
"""
import requests
import time
import os
from datetime import datetime

BASE_URL = "http://127.0.0.1:8080"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_health():
    try:
        return requests.get(f"{BASE_URL}/health", timeout=2).json()
    except:
        return None

def get_security_status():
    try:
        return requests.get(f"{BASE_URL}/security/status", timeout=2).json()
    except:
        return None

def get_tools():
    try:
        return requests.get(f"{BASE_URL}/tools", timeout=2).json()
    except:
        return []

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def display_dashboard():
    clear_screen()
    
    print("=" * 80)
    print("🚀 Agent Amigos Health Dashboard".center(80))
    print("=" * 80)
    print()
    
    # Health Check
    health = get_health()
    if health:
        print("📡 System Status")
        print("-" * 80)
        print(f"  Status: {'🟢 ONLINE' if health['status'] == 'online' else '🔴 OFFLINE'}")
        print(f"  Version: {health.get('version', 'Unknown')}")
        print(f"  Tools Available: {health.get('tools_available', 0)}")
        print(f"  LLM Ready: {'✅' if health.get('llm_ready') else '❌'}")
        print(f"  Model: {health.get('model', 'Unknown')}")
        print(f"  Server: {health.get('server', {}).get('host')}:{health.get('server', {}).get('port')}")
        print()
    else:
        print("❌ Backend Not Responding")
        print("   Start backend with: python backend/agent_init.py")
        print()
        return False
    
    # Security Status
    security = get_security_status()
    if security:
        print("🔒 Security Status")
        print("-" * 80)
        print(f"  Overall Status: {security.get('status', 'Unknown')}")
        print(f"  Security Score: {security.get('security_score', 0)}/100")
        print(f"  Autonomy: {'🟢 Enabled' if security.get('autonomy_enabled') else '🔴 Disabled'}")
        print(f"  Kill Switch: {'🔴 ACTIVE' if security.get('kill_switch') else '🟢 Inactive'}")
        print(f"  Allowed Actions: {len(security.get('allowed_actions', []))} categories")
        
        if security.get('issues'):
            print(f"  ⚠️ Issues: {len(security['issues'])}")
        if security.get('warnings'):
            print(f"  ⚠️ Warnings: {len(security['warnings'])}")
        print()
    
    # Tool Categories
    tools = get_tools()
    if tools:
        print("🔧 Tool Categories")
        print("-" * 80)
        
        categories = {}
        for tool in tools:
            # Try to categorize by name prefix
            name = tool.get('name', '')
            if name.startswith('canvas_'):
                cat = 'Canvas/Drawing'
            elif name.startswith('web_'):
                cat = 'Web/Browser'
            elif name.startswith('file_') or 'file' in name:
                cat = 'File System'
            elif 'memory' in name or 'remember' in name:
                cat = 'Memory'
            elif 'ollama' in name:
                cat = 'LLM/Ollama'
            elif 'window' in name or 'mouse' in name or 'key' in name:
                cat = 'Desktop Control'
            else:
                cat = 'General'
            
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count} tools")
        print()
    
    # System Info
    print("💻 System Information")
    print("-" * 80)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Owner: Darrell Buttigieg")
    print(f"  Mode: Amigos Agent")
    print()
    
    print("=" * 80)
    print("Press Ctrl+C to exit | Refreshing every 5 seconds...".center(80))
    print("=" * 80)
    
    return True

def main():
    print("Starting Agent Amigos Health Dashboard...")
    print("Connecting to http://127.0.0.1:8080...")
    time.sleep(1)
    
    try:
        while True:
            if not display_dashboard():
                time.sleep(5)
                continue
            time.sleep(5)
    except KeyboardInterrupt:
        clear_screen()
        print("\n👋 Dashboard closed. Agent Amigos is still running in the background.")
        print("   To stop the backend: Ctrl+C in the backend terminal\n")

if __name__ == "__main__":
    main()
