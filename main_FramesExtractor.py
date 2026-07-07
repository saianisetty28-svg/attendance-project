# =========================================================
# SECTION 1: IMPORTS
# =========================================================

import os
import time
from Frames_Extractor import extract_frames


# =========================================================
# SECTION 2: CONFIGURATION
# =========================================================

VIDEO_FOLDER = r"C:\Users\pranav h r\attendance_system\Videos\IN\1_02_R_20260407043954PM.mp4"
FRAME_FOLDER = r"C:\Users\pranav h r\attendance_system\Frames"
SKIP_N_FRAMES = 10

# OCR scans only until it detects the date, then frame extraction restarts from frame 0.
ENABLE_OCR = True
OCR_REGION = "top left"  # use "top left", "top", "bottom", or "full"


# =========================================================
# SECTION 3: RUNTIME HELPERS
# =========================================================

def format_seconds(seconds):
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours >= 1:
        return f"{int(hours)}h {int(minutes)}m {secs:.2f}s"
    if minutes >= 1:
        return f"{int(minutes)}m {secs:.2f}s"
    return f"{secs:.2f}s"


def timed_step(label, func, *args, **kwargs):
    start_time = time.perf_counter()
    print(f"START: {label}")

    result = func(*args, **kwargs)

    elapsed = time.perf_counter() - start_time
    print(f"END: {label} | runtime={format_seconds(elapsed)}")
    return result


# =========================================================
# SECTION 4: GET LOCAL VIDEOS
# =========================================================

def get_local_videos(video_folder):
    """
    Reads videos from a local file path or local folder.
    Returns list of (camera_id, video_path).
    """

    videos = []
    valid_extensions = (".mp4", ".avi", ".mov", ".mkv")

    if os.path.isfile(video_folder):
        file_name = os.path.basename(video_folder)
        if file_name.lower().endswith(valid_extensions):
            camera_id = file_name.split("_")[0]
            videos.append((camera_id, video_folder))
        return videos

    if not os.path.isdir(video_folder):
        print("ERROR: VIDEO_FOLDER does not exist or is not a directory:", video_folder)
        return videos

    for file_name in os.listdir(video_folder):
        if file_name.lower().endswith(valid_extensions):
            camera_id = file_name.split("_")[0]
            video_path = os.path.join(video_folder, file_name)
            videos.append((camera_id, video_path))

    return videos


# =========================================================
# SECTION 5: PROCESS SINGLE VIDEO
# =========================================================

def process_video(camera_id, video_path):
    print("\n=================================================")
    print(f"Processing Video: {video_path}")
    print(f"Camera ID: {camera_id}")
    print("=================================================")

    frames = extract_frames(
        video_id=os.path.basename(video_path),
        camera_id=camera_id,
        video_path=video_path,
        output_dir=FRAME_FOLDER,
        skip_n_frames=SKIP_N_FRAMES,
        enable_ocr=ENABLE_OCR,
        ocr_region=OCR_REGION,
    )

    print(f"Total Frames Extracted: {len(frames)}")
    return frames


# =========================================================
# SECTION 6: MAIN PIPELINE
# =========================================================

def run():
    total_start = time.perf_counter()
    print("Attendance Frame Extraction System Started\n")

    videos = timed_step("scan input videos", get_local_videos, VIDEO_FOLDER)

    if not videos:
        print("ERROR: No videos found:", VIDEO_FOLDER)
        return

    print(f"Found {len(videos)} videos\n")

    total_frames = 0
    for camera_id, video_path in videos:
        frames = timed_step(
            f"process video {os.path.basename(video_path)}",
            process_video,
            camera_id,
            video_path,
        )
        total_frames += len(frames)
        time.sleep(1)

    total_elapsed = time.perf_counter() - total_start
    print("\nALL VIDEOS PROCESSED SUCCESSFULLY")
    print(f"Total frames extracted: {total_frames}")
    print(f"Total runtime: {format_seconds(total_elapsed)}")


# =========================================================
# SECTION 7: ENTRY POINT
# =========================================================

if __name__ == "__main__":
    run()
