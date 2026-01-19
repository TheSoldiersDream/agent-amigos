import re

file_path = r"frontend/src/App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Import
content = content.replace('import ChalkBoardPanel from "./components/ChalkBoard";', 'import CanvasPanel from "./components/Canvas/CanvasPanel";')

# 2. Update State Variables and Setters
# Using regex to be safe, but simple replace might work if names are unique enough.
# chalkBoardOpen -> canvasOpen
content = content.replace("chalkBoardOpen", "canvasOpen")
content = content.replace("setChalkBoardOpen", "setCanvasOpen")

# chalkBoardCommands -> canvasCommands
content = content.replace("chalkBoardCommands", "canvasCommands")
content = content.replace("setChalkBoardCommands", "setCanvasCommands")

# chalkBoardSession -> canvasSession
content = content.replace("chalkBoardSession", "canvasSession")
content = content.replace("setChalkBoardSession", "setCanvasSession")

# 3. Update Component Usage
content = content.replace("<ChalkBoardPanel", "<CanvasPanel")
content = content.replace("</ChalkBoardPanel>", "</CanvasPanel>") # If it has children, though usually self-closing

# 4. Update API calls and strings
content = content.replace("/chalkboard/", "/canvas/")
content = content.replace("chalkboard_", "canvas_") # For filenames or IDs
content = content.replace('"chalkboard"', '"canvas"') # For tool names or strings
content = content.replace("'chalkboard'", "'canvas'")

# 5. Update Comments (Optional but good)
content = content.replace("CHALKBOARD", "CANVAS")
content = content.replace("ChalkBoard", "Canvas")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Updated {file_path}")
