from PIL import Image
from pathlib import Path

# Folder where this Python script is located
folder = Path(__file__).parent

input_path = folder / "CRr.png"
output_path = folder / "CRr_cropped.png"

img = Image.open(input_path).convert("RGBA")

# Find the bounding box of non-transparent pixels
bbox = img.getbbox()

if bbox:
    cropped = img.crop(bbox)
    cropped.save(output_path)

    print(f"Original size: {img.size}")
    print(f"Cropped size: {cropped.size}")
    print(f"Saved to: {output_path}")
else:
    print("Image is completely transparent.")