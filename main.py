# =========================================================
# SECTION 1: IMPORTS
# =========================================================

import os
import time
from Frames_Extractor import extract_frames


# =========================================================
# SECTION 2: CONFIGURATION
# =========================================================

VIDEO_FOLDER = "C:\\Users\\pranav h r\\attendance_system\\Videos\\sample_video.mp4"       # input videos (local)
FRAME_FOLDER = "C:\\Users\\pranav h r\\attendance_system\\Frames"       # output frames (local)
SKIP_N_FRAMES = 10            # adjust based on FPS (30 = ~1 sec if 30fps)


# =========================================================
# SECTION 3: GET LOCAL VIDEOS
# =========================================================

def get_local_videos(video_folder):
    """
    Reads all videos from local folder structure.
    Returns list of (camera_id, video_path)
    """

    videos = []

    # If user passed a single video file path, accept it
    if os.path.isfile(video_folder):
        file = os.path.basename(video_folder)
        if file.endswith((".mp4", ".avi")):
            camera_id = file.split("_")[0]
            videos.append((camera_id, video_folder))
        return videos

    # If it's not a directory, return empty list
    if not os.path.isdir(video_folder):
        print("❌ VIDEO_FOLDER does not exist or is not a directory:", video_folder)
        return videos

    for file in os.listdir(video_folder):
        if file.endswith((".mp4", ".avi")):
            # Example: cam1_video1.mp4 → cam1
            camera_id = file.split("_")[0]
            video_path = os.path.join(video_folder, file)
            videos.append((camera_id, video_path))

    return videos


# =========================================================
# SECTION 4: PROCESS SINGLE VIDEO
# =========================================================

def process_video(camera_id, video_path):

    print("\n=================================================")
    print(f"🎥 Processing Video: {video_path}")
    print(f"📷 Camera ID: {camera_id}")
    print("=================================================")

    frames = extract_frames(
        video_id=os.path.basename(video_path),
        camera_id=camera_id,
        video_path=video_path,
        output_dir=FRAME_FOLDER,
        skip_n_frames=SKIP_N_FRAMES
    )

    print(f"📸 Total Frames Extracted: {len(frames)}")


# =========================================================
# SECTION 5: MAIN PIPELINE
# =========================================================

def run():

    print("🔥 Attendance Frame Extraction System Started\n")

    videos = get_local_videos(VIDEO_FOLDER)

    if not videos:
        print("❌ No videos found in folder:", VIDEO_FOLDER)
        return

    print(f"✅ Found {len(videos)} videos\n")

    for camera_id, video_path in videos:

        process_video(camera_id, video_path)

        time.sleep(1)  # small delay for readability

    print("\n🎉 ALL VIDEOS PROCESSED SUCCESSFULLY")


# =========================================================
# SECTION 6: ENTRY POINT
# =========================================================

if __name__ == "__main__":
    run()