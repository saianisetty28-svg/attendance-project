import json
import os
import re
import time
from datetime import datetime

import cv2

from attendance_engine import AttendanceEngine
from embedding_loader import load_embeddings_from_db
from PSqlConnector import get_conn
from stabilizer import Stabilizer
from yolo_processor import process_frame

try:
    import pytesseract
except ImportError:
    pytesseract = None


FRAME_FOLDER = r"C:\Users\pranav h r\attendance_system\Frames\2026-04-07\1"


def find_frames(root_folder):
    """Recursively find all JPG frames under the provided root folder."""
    for base, _, files in os.walk(root_folder):
        for file in sorted(files):
            if file.lower().endswith((".jpg", ".jpeg")):
                yield os.path.join(base, file)


def _match_timestamp_from_text(text):
    patterns = [
        r"(20\d{2}\d{2}\d{2}\d{2}\d{2}\d{2}[APap][Mm])",
        r"(20\d{2}\d{2}\d{2}\d{2}\d{2}\d{2})",
        r"(20\d{2}-\d{2}-\d{2}[T_ -]\d{2}[:._-]\d{2}[:._-]\d{2})",
        r"(20\d{2}-\d{2}-\d{2}[T_ -]\d{2}[:._-]\d{2})",
        r"(20\d{2}-\d{2}-\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1)
            for fmt in [
                "%Y%m%d%I%M%S%p",
                "%Y%m%d%H%M%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H-%M-%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H-%M-%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(candidate, fmt)
                except ValueError:
                    continue
    return None


def _ocr_text_from_image(image, psm=7):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    _, thresh = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, inv_thresh = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    config = f"--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789:- "
    for source in (thresh, inv_thresh):
        try:
            text = pytesseract.image_to_string(source, config=config)
        except Exception:
            continue

        cleaned = re.sub(r"[^0-9A-Za-z:/., _-]", "", text)
        if cleaned:
            return cleaned

    return ""


def _extract_timestamp_from_frame(frame_path):
    if pytesseract is None:
        return None

    image = cv2.imread(frame_path)
    if image is None:
        return None

    height, width = image.shape[:2]
    crops = [
        ("top_left", image[0 : max(1, int(height * 0.08)), 0 : max(1, int(width * 0.45))]),
        ("top_band", image[0 : max(1, int(height * 0.12)), 0:width]),
        ("full", image),
    ]

    for region_name, crop in crops:
        if crop is None or crop.size == 0:
            continue

        text = _ocr_text_from_image(crop, psm=6)
        timestamp = _match_timestamp_from_text(text)
        if timestamp is not None:
            print(f"[OCR] extracted timestamp {timestamp} from {region_name}")
            return timestamp
        if text:
            print(f"[OCR] region {region_name} text: {text}")

    return None


def _is_extracted_frame_filename(frame_path):
    basename = os.path.basename(frame_path)
    return bool(re.search(r"frame_\d+", basename))


def get_frame_timestamp(frame_path, allow_ocr=False):
    if allow_ocr and pytesseract is not None:
        timestamp = _extract_timestamp_from_frame(frame_path)
        if timestamp is not None:
            return timestamp
        print(f"[OCR] no timestamp read from {os.path.basename(frame_path)}; falling back to filename/mtime")

    if not _is_extracted_frame_filename(frame_path):
        timestamp = parse_frame_timestamp(frame_path)
        if timestamp is not None:
            return timestamp

    try:
        return datetime.fromtimestamp(os.path.getmtime(frame_path))
    except Exception:
        return None


def parse_frame_timestamp(frame_path):
    path_text = os.path.abspath(frame_path)

    patterns = [
        r"(\d{14}[APap][Mm])",
        r"(\d{4}\d{2}\d{2}\d{2}\d{2}\d{2})",
        r"(\d{4}-\d{2}-\d{2}[T_ -]\d{2}[._-]\d{2}[._-]\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, path_text)
        if match:
            candidate = match.group(1)
            for fmt in [
                "%Y%m%d%I%M%S%p",
                "%Y%m%d%H%M%S",
                "%Y-%m-%d %H-%M-%S",
                "%Y-%m-%dT%H-%M-%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(candidate, fmt)
                except ValueError:
                    continue

    return None


def run():
    print("Loading employee embeddings from PostgreSQL...")

    employee_db, employee_meta = load_embeddings_from_db()
    if not employee_db:
        print("No active embeddings found in public.user_face_embeddings")
        return

    stabilizer = Stabilizer(window=3, min_score=0.15)
    conn = get_conn()
    engine = AttendanceEngine(conn=conn)

    start_time = time.perf_counter()
    print("Processing frames with YOLO + Face Recognition...\n")

    if not os.path.isdir(FRAME_FOLDER):
        print("❌ FRAME_FOLDER does not exist:", FRAME_FOLDER)
        return

    frame_count = 0
    event_count = 0

    for frame_path in find_frames(FRAME_FOLDER):
        frame_count += 1
        print(f"PROCESSING FRAME {frame_count}: {os.path.basename(frame_path)}")
        results, person_detected = process_frame(
            frame_path,
            employee_db,
            employee_meta=employee_meta,
            verbose=True,
            frame_id=frame_count,
        )

        event_timestamp = get_frame_timestamp(frame_path, allow_ocr=True)
        if event_timestamp is None:
            event_timestamp = datetime.fromtimestamp(os.path.getmtime(frame_path))

        if not results:
            if person_detected:
                print(f"    PERSON detected in frame {frame_count}, no face match results. Recording UNKNOWN event.")
                event = engine.create_event(
                    emp_id=None,
                    camera_id="CAM1",
                    confidence=0.0,
                    timestamp=event_timestamp,
                    user_id=None,
                    event_type="UNKNOWN",
                    notes="Person detected but face match or face extraction failed",
                    status="CREATED",
                )
                if event:
                    print(json.dumps(event, indent=4))
                    event_count += 1
            continue
        if event_timestamp is None:
            event_timestamp = datetime.fromtimestamp(os.path.getmtime(frame_path))

        for result in results:
            user_id = result.get("user_id")
            score = result.get("score", 0.0)
            accepted = result.get("accepted", False)

            if user_id is None:
                event = engine.create_event(
                    emp_id=None,
                    camera_id="CAM1",
                    confidence=score,
                    timestamp=event_timestamp,
                    user_id=None,
                    event_type="UNKNOWN",
                    notes="No confident employee match found",
                    status="CREATED",
                )
                if event:
                    print(json.dumps(event, indent=4))
                    event_count += 1
                continue

            confirmed = stabilizer.update(user_id, score=score, min_score=0.15)
            if confirmed:
                event = engine.create_event(
                    emp_id=confirmed,
                    camera_id="CAM1",
                    confidence=score,
                    timestamp=event_timestamp,
                    user_id=confirmed,
                    event_type="CHECKIN",
                    notes=f"Matched {employee_meta.get(confirmed, {}).get('full_name', 'employee')}",
                    status="CREATED",
                )
                if event:
                    print(json.dumps(event, indent=4))
                    event_count += 1
            else:
                if accepted:
                    print(f"    candidate {user_id} score={score:.4f} waiting for stability")
                else:
                    print(f"    candidate {user_id} score={score:.4f} below stable threshold")

    engine.close()
    elapsed = time.perf_counter() - start_time
    print(f"\nProcessed {frame_count} frames in {elapsed:.2f} seconds")
    print(f"Created {event_count} attendance events")


if __name__ == "__main__":
    run()