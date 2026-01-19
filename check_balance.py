
import re

def check_balance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)
    
    # Track parens and braces
    p_depth = 0
    b_depth = 0
    
    for i, char in enumerate(content):
        if char == '(': p_depth += 1
        elif char == ')': p_depth -= 1
        elif char == '{': b_depth += 1
        elif char == '}': b_depth -= 1
        
        # We don't care about JSX tags for now, as esbuild error is about parens/braces
    
    print(f"Final Paren Depth: {p_depth}")
    print(f"Final Brace Depth: {b_depth}")

check_balance('c:/Users/user/AgentAmigos/frontend/src/components/InternetConsole.jsx')
