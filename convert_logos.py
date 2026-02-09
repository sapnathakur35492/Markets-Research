from PIL import Image
import os

def convert_to_transparent(path):
    try:
        img = Image.open(path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            # Check for white (or near white) pixels
            if item[0] > 220 and item[1] > 220 and item[2] > 220:
                newData.append((255, 255, 255, 0))  # Set transparent
            else:
                newData.append(item)
        img.putdata(newData)
        new_path = path.replace(".jpg", ".png").replace(".jpeg", ".png")
        img.save(new_path, "PNG")
        print(f"Converted: {path} -> {new_path}")
    except Exception as e:
        print(f"Failed to convert {path}: {e}")

base_dir = "/home/aviox/Documents/Market-Research/static/images/"
files = ["IAF.jpg", "ISO9001.jpg", "ISO27001.jpg"]

for f in files:
    full_path = os.path.join(base_dir, f)
    if os.path.exists(full_path):
        convert_to_transparent(full_path)
    else:
        print(f"File not found: {full_path}")
