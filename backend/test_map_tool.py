
import agent_init
from agent_init import map_control

def test_map_control_output():
    result = map_control(place="London")
    print(f"Result: {result}")
    if "map_commands" in result:
        print("✅ map_commands found in result")
    else:
        print("❌ map_commands NOT found in result")

if __name__ == "__main__":
    test_map_control_output()
