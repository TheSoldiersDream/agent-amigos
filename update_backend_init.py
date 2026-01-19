import os

files = [
    r"backend/canvas/__init__.py"
]

replacements = [
    ("chalkboard_router", "canvas_router"),
    ("chalkboard_controller", "canvas_controller"),
    ("chalkboard_ai_assist", "canvas_ai_assist"),
    ("chalkboard_agent", "canvas_agent"),
    ("chalkboard_models", "canvas_models"),
    ("chalkboard_state", "canvas_state"),
    ("chalkboard_ai_routes", "canvas_ai_routes"),
    ("ChalkBoard", "Canvas"),
    ("chalkboard", "canvas"),
    ("CHALKBOARD", "CANVAS")
]

for file_path in files:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} (not found)")
        continue
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {file_path}")
