import os

import cv2
from insightface.app import FaceAnalysis
from ultralytics import YOLO

from face_matcher import find_best_match

# Architecture:
# - YOLO detects person boxes in each frame
# - InsightFace extracts embeddings from detected face regions
# - find_best_match compares embeddings to stored employee templates

YOLO_PERSON_MODEL = "yolov8n.pt"
YOLO_FACE_MODEL = "yolov8n-face.pt"
DEFAULT_YOLO_MODEL = YOLO_FACE_MODEL

model_path = YOLO_PERSON_MODEL if os.path.exists(YOLO_PERSON_MODEL) else DEFAULT_YOLO_MODEL
if model_path != YOLO_PERSON_MODEL:
    print(f"[yolo_processor] Warning: {YOLO_PERSON_MODEL} not found, falling back to {DEFAULT_YOLO_MODEL}")

yolo_model = YOLO(model_path)

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))


def process_frame(
    frame_path,
    employee_db,
    employee_meta=None,
    include_bbox=False,
    min_area=1024,
    min_conf=0.25,
    verbose=False,
    frame_id=None,
):
    """Process a frame with YOLO detection and return face-match results."""

    img = cv2.imread(frame_path)
    if img is None:
        if verbose:
            print(f"Failed to read image: {frame_path}")
        return [], False

    h, w = img.shape[:2]
    results = []
    person_detected = False

    if frame_id is not None:
        print(f"FRAME {frame_id}: {os.path.basename(frame_path)}")

    try:
        detections = yolo_model(img)[0]
    except Exception as exc:
        if verbose:
            print(f"YOLO inference error for {frame_path}: {exc}")
        return [], False

    for box in detections.boxes:
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

        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        area = (x2 - x1) * (y2 - y1)
        if area < min_area:
            continue

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

        class_name = None
        try:
            if hasattr(box, "cls") and len(box.cls) > 0:
                class_id = int(box.cls[0].item() if hasattr(box.cls[0], "item") else box.cls[0])
                names = getattr(yolo_model, "names", None)
                if isinstance(names, dict):
                    class_name = names.get(class_id)
                elif names is not None and isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
                    class_name = names[class_id]
        except Exception:
            class_name = None

        if class_name and class_name.lower() not in {"person", "face"}:
            continue

        person_detected = True
        person_crop = img[y1:y2, x1:x2]
        if person_crop.size == 0:
            continue

        try:
            faces = face_app.get(person_crop)
        except Exception as exc:
            if verbose:
                print(f"Face detection error for crop in {frame_path}: {exc}")
            continue

        if not faces:
            if verbose:
                print(f"    no faces found in person crop {x1,y1,x2,y2}")
            payload = {
                "user_id": None,
                "score": 0.0,
                "full_name": None,
                "issue": "no_face_detected",
            }
            if include_bbox:
                payload["bbox"] = (x1, y1, x2, y2)
            results.append(payload)
            continue

        for face in faces:
            embedding = face.embedding
            if embedding is None or getattr(embedding, 'size', 0) == 0:
                if verbose:
                    print(f"    invalid face embedding in crop {x1,y1,x2,y2}")
                payload = {
                    "user_id": None,
                    "score": 0.0,
                    "full_name": None,
                    "issue": "invalid_embedding",
                }
                if include_bbox:
                    payload["bbox"] = (x1, y1, x2, y2)
                results.append(payload)
                continue

            try:
                emp_id, score = find_best_match(
                    embedding,
                    employee_db,
                    threshold=0.20,
                    verbose=verbose,
                )
            except Exception as exc:
                if verbose:
                    print(f"find_best_match error: {exc}")
                continue

            accepted = score >= 0.20
            if verbose:
                print(f"    face detected; best_emp={emp_id} score={score:.4f} accepted={accepted}")

            match_meta = employee_meta.get(emp_id, {}) if employee_meta else {}
            payload = {
                "user_id": emp_id,
                "score": score,
                "full_name": match_meta.get("full_name"),
                "accepted": accepted,
            }

            if include_bbox:
                payload["bbox"] = (x1, y1, x2, y2)

            results.append(payload)

    return results, person_detected