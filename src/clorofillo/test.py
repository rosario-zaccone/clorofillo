#!/usr/bin/env python3
import sys
import os

DEFAULT_PATH = "/home/rosario/Documents/Projects/clorofillo/data/photos/test/patch/patch_17_after.png"

def dims_with_pil(path):
    from PIL import Image
    with Image.open(path) as img:
        return img.size  # (width, height)

def dims_with_cv2(path):
    import cv2
    img = cv2.imread(path)
    if img is None:
        raise RuntimeError("Cannot open image with cv2")
    h, w = img.shape[:2]
    return (w, h)

def print_dims(path):
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return
    try:
        w, h = dims_with_pil(path)
    except Exception:
        try:
            w, h = dims_with_cv2(path)
        except Exception as e:
            print(f"Failed to read image: {e}")
            return
    print(f"{os.path.basename(path)}: {w} x {h} (width x height)")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    print_dims(path)