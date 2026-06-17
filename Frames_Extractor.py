try:
    import cv2
except ImportError as e:
    raise ImportError(
        "Missing dependency: opencv-python. Install it with `pip install opencv-python` "
        "or `venv\\Scripts\\python.exe -m pip install opencv-python` from your project root."
    ) from e

import os
from datetime import datetime


def extract_frames(
    video_id,
    camera_id,
    video_path,
    output_dir="frames",
    skip_n_frames=10   # 👈 key parameter (e.g., 30 = 1 frame per second for 30fps video)
):

    # Create date-based camera folder: Frames/<YYYY-MM-DD>/<camera_id>
    date_folder = datetime.now().strftime("%Y-%m-%d")
    cam_folder = os.path.join(output_dir, date_folder, camera_id)
    os.makedirs(cam_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return []

    frame_count = 0
    saved_count = 0
    saved_paths = []

    print(f"▶ Processing Video ID {video_id} | Camera {camera_id}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 👇 Skip logic
        if frame_count % skip_n_frames == 0:
            frame_name = f"{video_id}_frame_{frame_count}.jpg"
            frame_path = os.path.join(cam_folder, frame_name)

            # Save frame locally
            cv2.imwrite(frame_path, frame)
            saved_paths.append(frame_path)
            saved_count += 1

        frame_count += 1

    cap.release()

    print(f"✅ Done Video {video_id}: Saved {saved_count} frames")
    return saved_paths