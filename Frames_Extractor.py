import csv
import os
import re
import time
from datetime import datetime

try:
    import cv2
except ImportError as e:
    raise ImportError(
        "Missing dependency: opencv-python. Install it with `pip install opencv-python` "
        "or `venv\\Scripts\\python.exe -m pip install opencv-python` from your project root."
    ) from e


def _quiet_opencv_logs():
    """Reduce noisy FFmpeg/OpenCV decoder logs when the installed OpenCV supports it."""
    try:
        cv2.setLogLevel(0)
    except Exception:
        pass


def _format_seconds(seconds):
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours >= 1:
        return f"{int(hours)}h {int(minutes)}m {secs:.2f}s"
    if minutes >= 1:
        return f"{int(minutes)}m {secs:.2f}s"
    return f"{secs:.2f}s"


def _load_tesseract():
    try:
        import pytesseract
    except ImportError:
        return None

    return pytesseract


def _crop_ocr_region(frame, region):
    region = (region or "full").strip().lower().replace("-", "_").replace(" ", "_")

    if region == "full":
        return frame

    height, width = frame.shape[:2]

    if region == "top":
        return frame[0 : max(1, height // 3), 0:width]
    if region == "bottom":
        return frame[max(0, height * 2 // 3) : height, 0:width]
    if region == "top_left":
        return frame[0 : max(1, height // 3), 0 : max(1, width // 2)]
    if region == "top_right":
        return frame[0 : max(1, height // 3), max(0, width // 2) : width]
    if region == "bottom_left":
        return frame[max(0, height * 2 // 3) : height, 0 : max(1, width // 2)]
    if region == "bottom_right":
        return frame[max(0, height * 2 // 3) : height, max(0, width // 2) : width]

    return frame


def _clean_ocr_text(text):
    text = " ".join(text.split())
    text = re.sub(r"[^0-9A-Za-z:/., _-]", "", text)
    return text.strip()


def _read_ocr_text(frame, pytesseract, region="bottom"):
    crop = _crop_ocr_region(frame, region)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    config = "--psm 6"
    text = pytesseract.image_to_string(thresh, config=config)
    return _clean_ocr_text(text)


def _write_ocr_results(csv_path, rows):
    if not rows:
        return

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["video_id", "camera_id", "frame_no", "video_time_sec", "frame_path", "ocr_text"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _date_from_filename(file_name):
    match = re.search(r"(20\d{2})(\d{2})(\d{2})", file_name)
    if not match:
        return None

    try:
        date_value = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return date_value.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _date_from_ocr_text(text):
    patterns = [
        r"(?P<year>20\d{2})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})",
        r"(?P<day>\d{1,2})[-/.](?P<month>\d{1,2})[-/.](?P<year>20\d{2})",
        r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        try:
            date_value = datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
            return date_value.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _open_video_capture(video_path):
    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap = cv2.VideoCapture(video_path)
    return cap


def _scan_video_date(
    cap,
    video_id,
    camera_id,
    fps,
    pytesseract,
    ocr_region,
):
    ocr_start = time.perf_counter()
    scan_frame_no = 0
    ocr_rows = []

    print("OCR date scan started. No frames are being saved during this scan.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            ocr_text = _read_ocr_text(frame, pytesseract, region=ocr_region)
        except Exception as e:
            print(f"WARNING: OCR scan failed and will stop: {e}")
            break

        detected_date = _date_from_ocr_text(ocr_text)
        ocr_rows.append(
            {
                "video_id": video_id,
                "camera_id": camera_id,
                "frame_no": scan_frame_no,
                "video_time_sec": round(scan_frame_no / fps, 3) if fps else "",
                "frame_path": "",
                "ocr_text": ocr_text,
            }
        )

        if detected_date:
            print(
                f"OCR detected date {detected_date} on frame {scan_frame_no} "
                f"({_format_seconds(time.perf_counter() - ocr_start)})"
            )
            return detected_date, ocr_rows

        if scan_frame_no == 0:
            print("OCR frame 0 did not contain a readable date. Checking next frames...")

        scan_frame_no += 1

    print(f"WARNING: OCR scan finished without finding a date ({_format_seconds(time.perf_counter() - ocr_start)})")
    return None, ocr_rows


def extract_frames(
    video_id,
    camera_id,
    video_path,
    output_dir="frames",
    skip_n_frames=10,
    enable_ocr=False,
    ocr_region="bottom",
    ocr_output_dir=None,
):
    start_time = time.perf_counter()
    _quiet_opencv_logs()

    if skip_n_frames <= 0:
        raise ValueError("skip_n_frames must be greater than 0")

    cap = _open_video_capture(video_path)

    if not cap.isOpened():
        print(f"ERROR: Cannot open video: {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    pytesseract = _load_tesseract() if enable_ocr else None
    if enable_ocr and pytesseract is None:
        print("WARNING: OCR enabled, but pytesseract is not installed. Frames will still be extracted.")

    print(f"Processing Video ID {video_id} | Camera {camera_id}")
    print(f"Video info: frames={total_frames or 'unknown'}, fps={fps or 'unknown'}, size={width}x{height}")

    date_folder = None
    ocr_rows = []

    if pytesseract is not None:
        date_folder, ocr_rows = _scan_video_date(
            cap,
            video_id,
            camera_id,
            fps,
            pytesseract,
            ocr_region,
        )

        cap.release()
        cap = _open_video_capture(video_path)

        if not cap.isOpened():
            print(f"ERROR: Cannot reopen video after OCR scan: {video_path}")
            return []

    if date_folder is None:
        date_folder = _date_from_filename(video_id)
        if date_folder:
            print(f"Using date from video filename: {date_folder}")
        else:
            date_folder = "unknown_date"
            print("WARNING: No date found from OCR or filename. Using folder: unknown_date")

    cam_folder = os.path.join(output_dir, date_folder, camera_id)
    os.makedirs(cam_folder, exist_ok=True)
    print(f"Frame output folder: {cam_folder}")

    frame_count = 0
    saved_count = 0
    failed_reads = 0
    saved_paths = []

    while True:
        ret, frame = cap.read()
        if not ret:
            current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES) or frame_count)
            if total_frames and current_pos < total_frames - 1:
                failed_reads += 1
                print(
                    "WARNING: Video read stopped before the expected end. "
                    f"pos={current_pos}, expected_frames={total_frames}"
                )
            break

        if frame_count % skip_n_frames == 0:
            frame_name = f"{video_id}_frame_{frame_count}.jpg"
            frame_path = os.path.join(cam_folder, frame_name)

            if cv2.imwrite(frame_path, frame):
                saved_paths.append(frame_path)
                saved_count += 1

                for ocr_row in ocr_rows:
                    if ocr_row["frame_no"] == frame_count:
                        ocr_row["frame_path"] = frame_path
                        break
            else:
                print(f"WARNING: Could not save frame: {frame_path}")

        frame_count += 1

    cap.release()

    if ocr_rows and date_folder is not None:
        safe_video_id = re.sub(r"[^0-9A-Za-z_.-]", "_", video_id)
        ocr_dir = ocr_output_dir or os.path.join(output_dir, date_folder, camera_id)
        ocr_csv_path = os.path.join(ocr_dir, f"{safe_video_id}_ocr.csv")
        _write_ocr_results(ocr_csv_path, ocr_rows)
        print(f"OCR CSV: {ocr_csv_path}")

    elapsed = time.perf_counter() - start_time
    print(
        f"Done Video {video_id}: saved={saved_count}, read_frames={frame_count}, "
        f"read_failures={failed_reads}, runtime={_format_seconds(elapsed)}"
    )

    if failed_reads:
        print(
            "HEVC decode note: early read failures usually mean the source video has corrupt packets "
            "or missing HEVC reference frames. Try re-encoding the video with ffmpeg if frames are missing."
        )

    return saved_paths
