import os
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw

def bezier_curve(points, steps=30):
    result = []
    for t in [i/steps for i in range(steps+1)]:
        x = (
            (1-t)**3 * points[0][0] +
            3*(1-t)**2 * t * points[1][0] +
            3*(1-t)*t**2 * points[2][0] +
            t**3 * points[3][0]
        )
        y = (
            (1-t)**3 * points[0][1] +
            3*(1-t)**2 * t * points[1][1] +
            3*(1-t)*t**2 * points[2][1] +
            t**3 * points[3][1]
        )
        result.append((x, y))
    return result

def draw_leaf(draw, base_x, base_y, length, width, flip=False):
    direction = -1 if flip else 1
    points_left = [
        (base_x, base_y),
        (base_x + direction * length * 0.3, base_y - width * 0.5),
        (base_x + direction * length * 0.7, base_y - width * 0.5),
        (base_x + direction * length, base_y)
    ]
    left_curve = bezier_curve(points_left)
    points_right = [
        (base_x + direction * length, base_y),
        (base_x + direction * length * 0.7, base_y + width * 0.5),
        (base_x + direction * length * 0.3, base_y + width * 0.5),
        (base_x, base_y)
    ]
    right_curve = bezier_curve(points_right)
    leaf_points = left_curve + right_curve
    green = (255, 165, 0)
    draw.polygon(leaf_points, fill=green)

def draw_stem(draw, base_x, base_y, height):
    points = []
    for i in range(height):
        x_offset = random.uniform(-1.5, 1.5)
        points.append((base_x + x_offset, base_y - i))
    stem_color = (20, 100, 20)
    draw.line(points, fill=stem_color, width=6)

def draw_plant(draw, frame, width, height):
    base_x = width // 2
    base_y = height - 10
    stem_height = 50 + int((frame / 99) * 400)
    draw_stem(draw, base_x, base_y, stem_height)
    max_leaves = 12
    num_leaves = int((frame / 99) * max_leaves)
    leaf_length = 60
    leaf_width = 30
    for i in range(num_leaves):
        y = base_y - int((i + 1) * (stem_height / (num_leaves + 1)))
        draw_leaf(draw, base_x, y, leaf_length, leaf_width, flip=False)
        draw_leaf(draw, base_x, y, leaf_length, leaf_width, flip=True)

def create_timelapse_images():
    output_dir = "data/photos/timelapse"
    os.makedirs(output_dir, exist_ok=True)

    width, height = 400, 600

    idvaso = input("Inserisci idvaso: ").strip()
    start_date = datetime(2024, 1, 1)

    for frame in range(100):
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw_plant(draw, frame, width, height)

        # Creazione del timestamp con formato specificato
        current_date = start_date + timedelta(days=frame)
        timestamp = current_date.strftime("%Y-%m-%d_%H-%M-%S")  # Formato richiesto
        filename = f"{idvaso}_{timestamp}.jpg"  # Nome del file con idvaso e timestamp

        # Salvataggio dell'immagine
        img.save(os.path.join(output_dir, filename))

    print(f"Generate 100 immagini in '{output_dir}/'")

if __name__ == "__main__":
    create_timelapse_images()
