import os

files = [
    r"frontend/src/components/Canvas/CanvasPanel.jsx",
    r"frontend/src/components/Canvas/CanvasSurface.jsx",
    r"frontend/src/components/Canvas/ToolsToolbar.jsx",
    r"frontend/src/components/Canvas/LayersPanel.jsx",
    r"frontend/src/App.jsx"
]

replacements = [
    ("Agent Amigos Chalk Board", "Agent Amigos Canvas"),
    ("CHALK BOARD PANEL", "CANVAS PANEL"),
    ("Chalk Board", "Canvas") # Catch all for comments and other labels
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
