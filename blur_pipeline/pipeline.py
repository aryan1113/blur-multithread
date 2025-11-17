from __future__ import annotations

from .audio import mux_audio
from .config import ProcessingConfig
from .processing import get_blur_strength, process_video

import random
import cv2


class VideoBlurPipeline:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.paths = config.derived_paths()

    def run(self) -> None:
        k_size = get_blur_strength(str(self.config.source_video))
        print(f"Selected Blur Kernel Size: {k_size}")

        self._render_sample(k_size)
        print(f"Sample saved to {self.paths.sample_final}")

        if not self._should_process_full():
            print("Aborted full processing.")
            return

        self._render_full(k_size)
        print(f"Full output saved to {self.config.output_video}")

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

        # FPS for time calculation
        cap = cv2.VideoCapture(str(self.config.source_video))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        start_sec = start_frame / fps if fps else 0
        end_frame = start_frame + sample_length - 1
        end_sec = end_frame / fps if fps else 0

        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h:02}:{m:02}:{s:02}"

        print(f"Sample frames: {start_frame} to {end_frame} (out of {total_frames})")
        print(f"Sample timestamps: {start_sec:.2f}s ({format_time(start_sec)}) to {end_sec:.2f}s ({format_time(end_sec)})")

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

