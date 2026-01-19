import os

files = [
    r"backend/canvas/canvas_router.py",
    r"backend/canvas/canvas_controller.py",
    r"backend/canvas/canvas_ai_assist.py",
    r"backend/canvas/canvas_agent.py",
    r"backend/canvas/canvas_models.py",
    r"backend/canvas/canvas_state.py",
    r"backend/routes/canvas_ai_routes.py",
    r"backend/agent_init.py",
    r"backend/dashboard.py" # Check this one too
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
        
    # Special case for imports that might have been missed or double replaced?
    # The order matters. "chalkboard_router" -> "canvas_router" handles the file import.
    # "chalkboard" -> "canvas" handles the rest.
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {file_path}")
