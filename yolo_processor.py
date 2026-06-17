import os
import cv2
from ultralytics import YOLO
from insightface.app import FaceAnalysis

from recognition.face_matcher import find_best_match

# Architecture:
# - YOLO detects face boxes in each frame
# - InsightFace extracts embeddings from detected faces
# - find_best_match compares embeddings to cached employee templates
# This keeps detection and recognition separate while using the existing matcher.

# ---------------------------
# Load models ONCE (important)
# ---------------------------

YOLO_FACE_MODEL = "yolov8n-face.pt"
DEFAULT_YOLO_MODEL = "yolov8n.pt"

model_path = YOLO_FACE_MODEL if os.path.exists(YOLO_FACE_MODEL) else DEFAULT_YOLO_MODEL
if model_path != YOLO_FACE_MODEL:
    print(f"[yolo_processor] Warning: {YOLO_FACE_MODEL} not found, falling back to {DEFAULT_YOLO_MODEL}")

yolo_model = YOLO(model_path)

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))


# ---------------------------
# Process Frame
# ---------------------------

def process_frame(
    frame_path,
    employee_db,
    include_bbox=False,
    min_area=1024,
    min_conf=0.25,
    verbose=False,
):
    """Process a single frame (path) and return face-match results.

    Parameters:
    - frame_path: path to image file
    - employee_db: embeddings database used by `find_best_match`
    - include_bbox: if True, each result is (emp_id, score, (x1,y1,x2,y2))
    - min_area: minimum person box area to consider
    - min_conf: minimum detection confidence to consider
    - verbose: print minimal debug info on errors

    Returns list of tuples: (emp_id, score) or (emp_id, score, bbox)
    """

    img = cv2.imread(frame_path)
    if img is None:
        if verbose:
            print(f"Failed to read image: {frame_path}")
        return []

    h, w = img.shape[:2]
    results = []

    # 1. YOLO FACE DETECTION (guarded)
    try:
        detections = yolo_model(img)[0]
    except Exception as e:
        if verbose:
            print(f"YOLO inference error for {frame_path}: {e}")
        return []

    for box in detections.boxes:
        # extract coords
        try:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
        except Exception:
            coords = getattr(box, "xyxy", None)
            if coords is None:
                continue
            try:
                coords = coords.cpu().numpy()[0]
                x1, y1, x2, y2 = map(int, coords)
            except Exception:
                continue

        # clamp to image bounds
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        area = (x2 - x1) * (y2 - y1)
        if area < min_area:
            continue

        # optional confidence filter
        conf = None
        if hasattr(box, "conf"):
            try:
                conf = float(box.conf[0])
            except Exception:
                try:
                    conf = float(box.conf)
                except Exception:
                    conf = None

        if conf is not None and conf < min_conf:
            continue

        person_crop = img[y1:y2, x1:x2]
        if person_crop.size == 0:
            continue

        # 2. FACE DETECTION (INSIGHTFACE) - guarded
        try:
            faces = face_app.get(person_crop)
        except Exception as e:
            if verbose:
                print(f"Face detection error for crop in {frame_path}: {e}")
            continue

        if not faces:
            continue

        for face in faces:
            embedding = face.embedding
            try:
                emp_id, score = find_best_match(embedding, employee_db)
            except Exception as e:
                if verbose:
                    print(f"find_best_match error: {e}")
                continue

            if include_bbox:
                results.append((emp_id, score, (x1, y1, x2, y2)))
            else:
                results.append((emp_id, score))

    return results