import subprocess
import json

def get_frame_timestamp(video_path: str, frame_number: int) -> float:
    """
    Uses ffprobe to get the exact timestamp (in seconds) of a given frame number.
    """
    # ffprobe command to get frame info as JSON
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", f"frame=pkt_pts_time",
        "-read_intervals", f"%{{{frame_number}}}",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    frames = data.get("frames", [])
    if not frames:
        raise ValueError(f"No frame found at index {frame_number}")
    # pkt_pts_time is the timestamp in seconds
    return float(frames[0]["pkt_pts_time"])

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python get_frame_timestamp.py <video_path> <frame_number>")
        sys.exit(1)
    video_path = sys.argv[1]
    frame_number = int(sys.argv[2])
    ts = get_frame_timestamp(video_path, frame_number)
    print(f"Frame {frame_number} timestamp: {ts:.6f} seconds")
