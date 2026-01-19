import os

files = [
    r"frontend/src/components/Canvas/index.js",
    r"frontend/src/components/Sidebar.jsx"
]

replacements = [
    ("ChalkBoardPanel", "CanvasPanel"),
    ("ChalkBoard", "Canvas"),
    ("chalkboard", "canvas"),
    ("Chalk Board", "Canvas") # For the label in Sidebar
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
