import sys
from pathlib import Path
sys.path.insert(0, str(Path('backend').resolve()))
from tools.media_tools import media

out_dir = Path('backend/media_outputs/images')
out_dir.mkdir(parents=True, exist_ok=True)
res = media._generate_with_pollinations(
    prompt='Colorful abstract pattern with vibrant gradients, digital art',
    negative_prompt='',
    width=512,
    height=512,
    output_path=out_dir,
    idx=0,
    style='default'
)
print(res)