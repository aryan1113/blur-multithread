from pathlib import Path

from blur_pipeline.config import ProcessingConfig
from blur_pipeline.pipeline import VideoBlurPipeline


def main() -> None:
    config = ProcessingConfig(
        source_video=Path("../Tuesday.mp4"),
        output_video=Path("results/blurred_output.mp4"),
        sample_frames=500,
    )
    VideoBlurPipeline(config).run()


if __name__ == "__main__":
    main()

