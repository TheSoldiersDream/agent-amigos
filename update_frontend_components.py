import os

files = [
    r"frontend/src/components/Canvas/CanvasPanel.jsx",
    r"frontend/src/components/Canvas/CanvasAIPanel.jsx"
]

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content.replace("ChalkBoard", "Canvas")
    new_content = new_content.replace("chalkboard", "canvas")
    new_content = new_content.replace("Chalkboard", "Canvas") # Just in case
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {file_path}")
