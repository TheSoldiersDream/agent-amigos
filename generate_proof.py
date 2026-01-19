import sys
import os

# Set working directory to the project root
ROOT = r"c:\Users\user\AgentAmigos"
os.chdir(ROOT)
sys.path.append(ROOT)
sys.path.append(os.path.join(ROOT, "backend"))

from backend.tools import media_tools

print("Generating proof video...")
# Use the instance 'media' inside the module 'media_tools'
result = media_tools.media.create_video_from_prompt("A high-tech digital environment showing Agent Amigos collaborating with Darrell Buttigieg to build the future of AI.")
print(f"Result: {result}")
