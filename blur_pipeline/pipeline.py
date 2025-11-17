from __future__ import annotations

from .audio import mux_audio
from .config import ProcessingConfig
from .processing import get_blur_strength, process_video

import random
import cv2
import subprocess
import json


class VideoBlurPipeline:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.paths = config.derived_paths()

    def run(self, skip_sample: bool = False) -> None:
        k_size = get_blur_strength(str(self.config.source_video))
        print(f"[DEBUG] Selected Blur Kernel Size: {k_size}")

        if not skip_sample:
            print("[DEBUG] Starting sample frame creation...")
            self._render_sample(k_size)
            print(f"[DEBUG] Sample saved to {self.paths.sample_final}")
            print("[DEBUG] Sample frame creation complete.")
        else:
            print("[DEBUG] Skipping sample creation (--skip-sample set)")

        print("[DEBUG] Starting blurred output sample creation...")
        if not self._should_process_full():
            print("[DEBUG] Aborted full processing.")
            return

        print("[DEBUG] Starting full blurred output file creation...")
        self._render_full(k_size)
        print(f"[DEBUG] Full output saved to {self.config.output_video}")
        print("[DEBUG] Full blurred output file creation complete.")

    def _render_sample(self, k_size: int) -> None:

        print(f"Creating sample ({self.config.sample_frames} frames) ...")

        cap = cv2.VideoCapture(str(self.config.source_video))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        sample_length = self.config.sample_frames
        if total_frames > sample_length:
            max_start = total_frames - sample_length
            start_frame = random.randint(0, max_start)
        else:
            start_frame = 0

        # Use ffprobe to get the exact timestamp for the start frame

        def get_frame_timestamp(video_path: str, frame_number: int) -> float:
            # Fast: estimate time, then probe a window around it, fallback to estimate if needed
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            if not fps or fps <= 0:
                raise RuntimeError("Could not determine FPS for timestamp estimation.")
            est_time = frame_number / fps

            # using a larger window will most likely NOT help
            for window in [0.5, 2, 5, 10, 15, 20, 25, 30, 50]:
                start = max(0, est_time - window)
                end = est_time + window
                cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "frame=pkt_pts_time",
                    "-read_intervals", f"{start}%{end}",
                    "-of", "json",
                    video_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    continue
                data = json.loads(result.stdout)
                frames = data.get("frames", [])
                frames_with_pts = [f for f in frames if "pkt_pts_time" in f]
                if frames_with_pts:
                    closest = min(frames_with_pts, key=lambda f: abs(float(f["pkt_pts_time"]) - est_time))
                    return float(closest["pkt_pts_time"])

            # Fallback: use estimate
            print(f"Warning: No frame timestamp found with ffprobe, falling back to estimate {est_time:.6f}s.")
            return est_time

        video_path_str = str(self.config.source_video)
        start_sec = get_frame_timestamp(video_path_str, start_frame)

        # FPS for time calculation (for end frame estimate only)
        cap = cv2.VideoCapture(video_path_str)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        end_frame = start_frame + sample_length - 1
        end_sec = end_frame / fps if fps else 0

        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h:02}:{m:02}:{s:02}"

        print(f"Sample frames: {start_frame} to {end_frame} (out of {total_frames})")
        print(f"Sample start timestamp (exact): {start_sec:.6f}s ({format_time(start_sec)})")
        print(f"Sample end frame (approx): {end_frame} at {end_sec:.2f}s ({format_time(end_sec)})")

        sample_video = process_video(
            str(self.config.source_video),
            str(self.paths.sample_video_only),
            k_size,
            max_frames=sample_length,
            description="Sample",
            start_frame=start_frame,
        )
        mux_audio(
            str(self.config.source_video),
            str(sample_video.path),
            str(self.paths.sample_final),
            duration=sample_video.duration,
            audio_offset=start_sec,
        )

    def _render_full(self, k_size: int) -> None:
        full_video = process_video(
            str(self.config.source_video),
            str(self.paths.full_video_only),
            k_size,
            max_frames=None,
            description="Full Video",
        )
        mux_audio(
            str(self.config.source_video),
            str(full_video.path),
            str(self.config.output_video),
            duration=full_video.duration,
        )

    @staticmethod
    def _should_process_full() -> bool:
        response = input("Type YES to process the entire video: ").strip().upper()
        return response == "YES"

