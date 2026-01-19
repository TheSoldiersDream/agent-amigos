import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from tools.media_tools import media

# Ensure output directory exists
os.makedirs("media_outputs/images", exist_ok=True)

video_path = "media_outputs/videos/Charger_Rebuild.mp4"
output_image_path = "media_outputs/images/Charger_Rebuild_frame.png"

print(f"Extracting frame from {video_path}...")
try:
    # Extract frame at 1 second
    res = media.extract_frame(video_path, 1.0, output_image_path)
    print("Result:", res)
except Exception as e:
    print("Error:", e)
