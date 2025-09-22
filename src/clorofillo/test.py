import cv2
import numpy as np
import base64
import os
from dotenv import load_dotenv

load_dotenv()

PATCH_MIN_WIDTH = int(os.getenv("PATCH_MIN_WIDTH", 60))
PATCH_MIN_HEIGHT = int(os.getenv("PATCH_MIN_HEIGHT", 60))
COLOR_DIFF_THRESH = int(os.getenv("COLOR_DIFF_THRESH", 35))
BLUR_KERNEL_SIZE = int(os.getenv("BLUR_KERNEL_SIZE", 5))
MORPH_KERNEL_SIZE = int(os.getenv("MORPH_KERNEL_SIZE", 3))
MORPH_DILATE_ITER = int(os.getenv("MORPH_DILATE_ITER", 2))

def detect_insect_patches_base64(before_path, after_path):
    if not os.path.exists(before_path) or not os.path.exists(after_path):
        return []

    before = cv2.imread(before_path)
    after = cv2.imread(after_path)
    if before is None or after is None:
        return []

    orb = cv2.ORB_create(1000)
    kp1, des1 = orb.detectAndCompute(before, None)
    kp2, des2 = orb.detectAndCompute(after, None)
    if des1 is None or des2 is None:
        return []

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda x: x.distance)
    if len(matches) < 4:
        return []

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
    M, _ = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 4.0)
    aligned_after = cv2.warpPerspective(after, M, (before.shape[1], before.shape[0]))

    blur_ksize = (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE)
    morph_kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)

    before_blur = cv2.GaussianBlur(before, blur_ksize, 0)
    after_blur = cv2.GaussianBlur(aligned_after, blur_ksize, 0)

    lab_before = cv2.cvtColor(before_blur, cv2.COLOR_BGR2LAB)
    lab_after = cv2.cvtColor(after_blur, cv2.COLOR_BGR2LAB)
    diff = cv2.absdiff(lab_before, lab_after)
    dist = np.sqrt(np.sum(np.square(diff.astype(np.float32)), axis=2)).astype(np.uint8)

    _, mask = cv2.threshold(dist, COLOR_DIFF_THRESH, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, morph_kernel)
    mask = cv2.dilate(mask, None, iterations=MORPH_DILATE_ITER)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    os.makedirs("data/photos/test/patch", exist_ok=True)
    patches_b64 = []
    i = 0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if w < PATCH_MIN_WIDTH or h < PATCH_MIN_HEIGHT:
            continue

        patch = aligned_after[y:y+h, x:x+w]
        patch_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        if patch_gray.std() < 10:
            continue

        _, buffer = cv2.imencode('.jpg', patch)
        b64 = base64.b64encode(buffer).decode('utf-8')
        patches_b64.append(b64)
        with open(f"data/photos/test/patch/patch_{i}.jpg", "wb") as f:
            f.write(base64.b64decode(b64))
        i += 1

    return patches_b64

detect_insect_patches_base64("/home/rosario/Documents/Projects/clorofillo/data/photos/test/a.jpg","/home/rosario/Documents/Projects/clorofillo/data/photos/test/insect.jpg")
