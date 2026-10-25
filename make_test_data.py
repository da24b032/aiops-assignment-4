"""Generate random coloured-circle images and bundle them into 5/20/50-image ZIPs for load tests.
Run: python make_test_data.py   (output goes to ./test_data/)"""
import os
import random
import zipfile

from PIL import Image, ImageDraw

os.makedirs("test_data/images", exist_ok=True)


def draw_image(path, size=(640, 480)):
    img = Image.new("RGB", size, tuple(random.randint(0, 255) for _ in range(3)))
    d = ImageDraw.Draw(img)
    for _ in range(12):
        x0, y0 = random.randint(0, size[0] - 50), random.randint(0, size[1] - 50)
        d.ellipse(
            [x0, y0, x0 + random.randint(40, 200), y0 + random.randint(40, 200)],
            fill=tuple(random.randint(0, 255) for _ in range(3)),
        )
    img.save(path)


all_paths = []
for i in range(60):
    p = f"test_data/images/img_{i:03d}.jpg"
    draw_image(p)
    all_paths.append(p)

for zip_name, n in [("bulk_5.zip", 5), ("bulk_20.zip", 20), ("bulk_50.zip", 50)]:
    with zipfile.ZipFile(f"test_data/{zip_name}", "w") as z:
        for p in all_paths[:n]:
            z.write(p, os.path.basename(p))
print("Wrote test_data/ (single images + bulk_5/20/50.zip)")
