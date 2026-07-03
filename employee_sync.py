import os
import re

import cv2
import numpy as np
from psycopg2.extras import Json, RealDictCursor
from insightface.app import FaceAnalysis

from PSqlConnector import get_conn


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMPLOYEES_DIR = os.path.join(BASE_DIR, "Employess")
MODEL_NAME = "buffalo_l"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

app = FaceAnalysis(name=MODEL_NAME)
app.prepare(ctx_id=0, det_size=(640, 640))


def normalize_name(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def fetch_users():
    query = """
        SELECT user_id, full_name, empcode
        FROM public.users
        WHERE full_name IS NOT NULL
        ORDER BY user_id
    """

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    users_by_name = {}
    duplicate_names = set()

    for row in rows:
        normalized = normalize_name(row.get("full_name"))
        if not normalized:
            continue
        if normalized in users_by_name:
            duplicate_names.add(normalized)
        users_by_name[normalized] = row

    if duplicate_names:
        print("WARNING: Duplicate full_name values found in public.users:")
        for name in sorted(duplicate_names):
            print(f" - {name}")
        print("Only the last row returned by user_id order will be used for duplicate names.")

    print(f"Loaded {len(users_by_name)} users from public.users")
    return users_by_name


def iter_employee_folders(employees_dir=EMPLOYEES_DIR):
    if not os.path.isdir(employees_dir):
        print(f"ERROR: Employee image folder does not exist: {employees_dir}")
        return

    for entry in sorted(os.scandir(employees_dir), key=lambda item: item.name.casefold()):
        if entry.is_dir():
            yield entry


def iter_image_paths(folder_path):
    for entry in sorted(os.scandir(folder_path), key=lambda item: item.name.casefold()):
        if not entry.is_file():
            continue
        _, ext = os.path.splitext(entry.name)
        if ext.casefold() in IMAGE_EXTENSIONS:
            yield entry.path


def choose_largest_face(faces):
    return max(
        faces,
        key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]),
    )


def generate_embedding_from_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"WARNING: Could not read image: {image_path}")
        return None

    faces = app.get(img)
    if not faces:
        print(f"WARNING: No face found in image: {image_path}")
        return None

    face = choose_largest_face(faces)
    embedding = np.asarray(face.embedding, dtype=np.float32)
    return embedding.tolist()


def generate_embeddings_for_folder(folder_path):
    embeddings = []

    image_paths = list(iter_image_paths(folder_path))
    if not image_paths:
        print(f"WARNING: No supported images found in folder: {folder_path}")
        return embeddings

    for image_path in image_paths:
        embedding = generate_embedding_from_image(image_path)
        if embedding is None:
            continue
        embeddings.append(
            {
                "image_path": image_path,
                "embedding": embedding,
                "dimension": len(embedding),
            }
        )
        print(f"Generated embedding from {os.path.basename(image_path)}")

    return embeddings


def fetch_existing_embedding_ids(cursor, user_id):
    cursor.execute(
        """
        SELECT embedding_id
        FROM public.user_face_embeddings
        WHERE user_id = %s
          AND model_name = %s
          AND is_active = TRUE
        ORDER BY embedding_id
        """,
        (user_id, MODEL_NAME),
    )
    return [row["embedding_id"] for row in cursor.fetchall()]


def sync_user_embeddings(cursor, user_id, embeddings):
    existing_ids = fetch_existing_embedding_ids(cursor, user_id)
    update_count = min(len(existing_ids), len(embeddings))

    for index in range(update_count):
        embedding_data = embeddings[index]
        cursor.execute(
            """
            UPDATE public.user_face_embeddings
            SET image_id = NULL,
                embedding = %s,
                embedding_dimension = %s,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE embedding_id = %s
            """,
            (
                Json(embedding_data["embedding"]),
                embedding_data["dimension"],
                existing_ids[index],
            ),
        )

    for embedding_data in embeddings[update_count:]:
        cursor.execute(
            """
            INSERT INTO public.user_face_embeddings
                (user_id, image_id, model_name, embedding, embedding_dimension, is_active)
            VALUES
                (%s, NULL, %s, %s, %s, TRUE)
            """,
            (
                user_id,
                MODEL_NAME,
                Json(embedding_data["embedding"]),
                embedding_data["dimension"],
            ),
        )

    inactive_ids = existing_ids[update_count:]
    if inactive_ids:
        cursor.execute(
            """
            UPDATE public.user_face_embeddings
            SET is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE embedding_id = ANY(%s)
            """,
            (inactive_ids,),
        )

    return {
        "updated": update_count,
        "inserted": len(embeddings) - update_count,
        "deactivated": len(inactive_ids),
    }


def generate_embeddings_from_employee_folders(employees_dir=EMPLOYEES_DIR):
    users_by_name = fetch_users()

    matched_users = 0
    total_generated = 0
    total_updated = 0
    total_inserted = 0
    total_deactivated = 0

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for folder in iter_employee_folders(employees_dir):
                folder_name = folder.name
                user = users_by_name.get(normalize_name(folder_name))

                if user is None:
                    print(f"WARNING: No public.users match found for folder: {folder_name}")
                    continue

                user_id = user["user_id"]
                print(f"\nProcessing {folder_name} -> user_id={user_id}")

                embeddings = generate_embeddings_for_folder(folder.path)
                if not embeddings:
                    print(f"WARNING: No valid embeddings generated for {folder_name}")
                    continue

                result = sync_user_embeddings(cursor, user_id, embeddings)
                matched_users += 1
                total_generated += len(embeddings)
                total_updated += result["updated"]
                total_inserted += result["inserted"]
                total_deactivated += result["deactivated"]

                print(
                    f"Synced {folder_name}: "
                    f"{result['updated']} updated, "
                    f"{result['inserted']} inserted, "
                    f"{result['deactivated']} deactivated"
                )

        conn.commit()

    print("\nEmbedding sync complete.")
    print(f"Matched users: {matched_users}")
    print(f"Generated embeddings: {total_generated}")
    print(f"Updated rows: {total_updated}")
    print(f"Inserted rows: {total_inserted}")
    print(f"Deactivated rows: {total_deactivated}")


if __name__ == "__main__":
    generate_embeddings_from_employee_folders()
