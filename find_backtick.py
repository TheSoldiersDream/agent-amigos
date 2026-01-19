
def find_unterminated_backtick(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_backtick = False
    last_backtick_line = -1
    
    for i, line in enumerate(lines):
        # Find all backticks that are not escaped
        # This is still a bit simple but better
        j = 0
        while j < len(line):
            if line[j] == '`':
                if j == 0 or line[j-1] != '\\':
                    in_backtick = not in_backtick
                    if in_backtick:
                        last_backtick_line = i + 1
                        last_backtick_col = j + 1
            j += 1
    
    if in_backtick:
        print(f"Unterminated backtick starting at line {last_backtick_line}, col {last_backtick_col}")
    else:
        print("All backticks seem terminated.")
    
    if in_backtick:
        print(f"Unterminated backtick starting around line {last_backtick_line}")
    else:
        print("All backticks seem terminated (or balanced per line).")

find_unterminated_backtick('c:/Users/user/AgentAmigos/frontend/src/App.jsx')
