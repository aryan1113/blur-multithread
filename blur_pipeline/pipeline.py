from __future__ import annotations

from .audio import mux_audio
from .config import ProcessingConfig
from .processing import get_blur_strength, process_video


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
        sample_video = process_video(
            str(self.config.source_video),
            str(self.paths.sample_video_only),
            k_size,
            max_frames=self.config.sample_frames,
            description="Sample",
        )
        mux_audio(
            str(self.config.source_video),
            str(sample_video.path),
            str(self.paths.sample_final),
            duration=sample_video.duration,
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

