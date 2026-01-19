
def list_backticks(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    backticks = []
    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            if line[j] == '`':
                if j == 0 or line[j-1] != '\\':
                    backticks.append((i + 1, j + 1))
            j += 1
    
    print(f"Total backticks: {len(backticks)}")
    for i in range(len(backticks)):
        if i > 700:
            print(f"Index {i}: {backticks[i]}")

list_backticks('c:/Users/user/AgentAmigos/frontend/src/App.jsx')
