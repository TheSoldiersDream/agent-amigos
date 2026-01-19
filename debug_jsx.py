import re

def check_jsx_balance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    depth = 0
    stack = []
    
    # Simple regex for <div> and </div>
    # This is naive but might help find the major imbalance
    open_div = re.compile(r'<div(?![^>]*/>)\b')
    close_div = re.compile(r'</div\b')

    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Count openings
        openings = open_div.findall(line)
        for _ in openings:
            depth += 1
            stack.append(line_num)
            
        # Count closings
        closings = close_div.findall(line)
        for _ in closings:
            depth -= 1
            if stack:
                stack.pop()
            else:
                print(f"Extra closing </div> at line {line_num}")

    print(f"Final depth: {depth}")
    if stack:
        print(f"Unclosed <div> tags opened at lines: {stack[-20:]}") # Show last 20

if __name__ == "__main__":
    check_jsx_balance(r'c:\Users\user\AgentAmigos\frontend\src\App.jsx')
