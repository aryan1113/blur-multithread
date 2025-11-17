from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Optional

import cv2
from tqdm import tqdm

from .config import ProcessedVideo


def get_blur_strength(path: str) -> int:
    cap = cv2.VideoCapture(path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        cap.release()
        sys.exit("Error reading video file.")

    cap.set(cv2.CAP_PROP_POS_FRAMES, random.randint(0, total_frames - 1))
    ret, frame = cap.read()
    cap.release()

    if not ret:
        sys.exit("Error reading video file.")

    cv2.ocl.setUseOpenCL(True)
    umat_frame = cv2.UMat(frame)

    window = "Preview (Adjust Slider, Press SPACE to Start)"
    cv2.namedWindow(window)
    val = [0]

    def on_track(v: int) -> None:
        val[0] = v
        k = max(1, 2 * v + 1)
        preview = cv2.blur(umat_frame, (k, k))
        cv2.imshow(window, preview)

    cv2.createTrackbar("Strength", window, 0, 50, on_track)
    on_track(0)

    while True:
        key = cv2.waitKey(1) & 0xFF
        # Space to confirm, Esc to exit
        if key == 32:
            break
        if key == 27:
            sys.exit("Cancelled.")

    cv2.destroyAllWindows()
    return max(1, 2 * val[0] + 1)


def process_video(
    input_path: str,
    output_path: str,
    k_size: int,
    max_frames: Optional[int],
    description: str,
) -> ProcessedVideo:
    cap = cv2.VideoCapture(input_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0 or not cap.isOpened():
        cap.release()
        raise RuntimeError("Unable to read video metadata.")

    frames_to_process = min(total_frames, max_frames) if max_frames else total_frames

    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    cv2.ocl.setUseOpenCL(True)

    pbar = tqdm(total=frames_to_process, desc=description, unit="frame")
    processed = 0

    while processed < frames_to_process:
        ret, frame = cap.read()
        if not ret:
            break

        umat = cv2.UMat(frame)
        blurred = cv2.blur(umat, (k_size, k_size))
        out.write(blurred.get())

        processed += 1
        pbar.update(1)

    pbar.close()
    cap.release()
    out.release()
    print(f"{description} complete ({processed} frames).")
    return ProcessedVideo(path=Path(output_path), frame_count=processed, fps=fps)

