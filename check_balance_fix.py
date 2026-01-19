import re

def check_balance(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove comments to avoid false positives
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    content = re.sub(r"//.*", "", content)
    
    lines = content.split("\n")
    p_depth = 0
    b_depth = 0
    for i, line in enumerate(lines):
        for char in line:
            if char == "(": p_depth += 1
            elif char == ")": p_depth -= 1
            elif char == "{": b_depth += 1
            elif char == "}": b_depth -= 1
        
        if b_depth < 0:
            print(f"ERROR: Brace depth negative at line {i+1}: {line.strip()}")
            # return
        if p_depth < 0:
            print(f"ERROR: Paren depth negative at line {i+1}: {line.strip()}")
            # return
    
    print(f"Finished. Final Paren Depth: {p_depth}, Final Brace Depth: {b_depth}")

check_balance("c:/Users/user/AgentAmigos/frontend/src/components/InternetConsole.jsx")
