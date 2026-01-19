import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from tools.media_tools import media

# Ensure output directory exists
os.makedirs("media_outputs/videos", exist_ok=True)

image_path = "media_outputs/images/Charger_Rebuild_frame.png"

print(f"Testing restoration on {image_path}...")
try:
    # Force use of pollinations to verify the fix
    res = media.restore_vehicle_video(
        image_path=image_path,
        duration=5,
        model="pollinations",
        extra_notes="Paint: Midnight Blue | Intensity: High"
    )
    print("Result:", res)
except Exception as e:
    print("Error:", e)
