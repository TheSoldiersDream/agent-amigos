import json
import traceback

try:
    from backend.tools.shop_tools import search_products
    res = search_products("starlink kit philippines", region="PH", currencies=["AUD", "PHP"], limit=8)
    print(json.dumps({"success": True, "results": res}, ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e), "traceback": traceback.format_exc()}, ensure_ascii=False))
