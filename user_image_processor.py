import os
import cv2
import json
import numpy as np
from PIL import Image
import pillow_heif
from insightface.app import FaceAnalysis

from PsqlConnector import get_conn

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

IMAGE_DIR = r"C:\Users\anjan\Attendance\goldenEye\Employee Images"

print("Loading InsightFace model...")
app = FaceAnalysis(name="buffalo_l")
app.prepare(
    ctx_id=0,
    det_size=(640, 640))
print("✅ InsightFace model loaded.\n")


# ---------------------------------------
# Read active users from PostgreSQL
# ---------------------------------------
def get_users():

    conn = get_conn()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    user_id,
                    full_name
                FROM users
                WHERE is_active = TRUE
                ORDER BY user_id
            """)

            users = cursor.fetchall()

            return users

    finally:

        conn.close()


# ---------------------------------------
# Save embedding to database
# ---------------------------------------
def save_embedding(user_id, embedding):

    conn = get_conn()

    try:

        with conn.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO user_face_embeddings
                (
                    user_id,
                    image_id,
                    model_name,
                    embedding,
                    embedding_dimension,
                    is_active
                )
                VALUES
                (
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s,
                    TRUE
                )
                """,
                (
                    user_id,
                    "buffalo_l",
                    json.dumps(embedding.tolist()),
                    len(embedding)
                )
            )

        conn.commit()
        print(f"✅ Embedding saved for User ID : {user_id}")

    finally:

        conn.close()


# ---------------------------------------
# Check user folders
# ---------------------------------------
def check_user_folders(users):

    print("\nChecking Employee Image folders...\n")

    for user_id, full_name in users:

        if full_name.lower() == "unidentified":
            continue

        folder_path = os.path.join(
            IMAGE_DIR,
            full_name
        )

        if not os.path.isdir(folder_path):
            continue

        print("----------------------------------------")
        print(f"User ID   : {user_id}")
        print(f"Full Name  : {full_name}")
        print(f"Folder    : {folder_path}")
        print("✅ Folder Found")


# ---------------------------------------
# Read images using OpenCV
# ---------------------------------------
def read_image(image_path):
    """
    Read image from file, with support for HEIC format
    """
    if image_path.lower().endswith((".heic", ".heif")):
        try:
            # Use Pillow to open HEIC file
            pil_image = Image.open(image_path)
            # Convert PIL Image to OpenCV format (BGR)
            img_array = np.array(pil_image)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # Convert RGB to BGR for OpenCV
                img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img = img_array
            return img
        except Exception as e:
            print(f"⚠️  Error reading HEIC file: {e}")
            return None
    else:
        # Use OpenCV for standard formats
        return cv2.imread(image_path)


# ---------------------------------------
# Read images using OpenCV
# ---------------------------------------
def read_user_images(users):

    print("\nReading user images...\n")

    for user_id, full_name in users:

        if full_name.lower() == "unidentified":
            continue

        folder_path = os.path.join(
            IMAGE_DIR,
            full_name
        )

        if not os.path.isdir(folder_path):
            continue

        image_files = []

        for file in sorted(os.listdir(folder_path)):

            if file.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")):
                image_files.append(file)

        print("----------------------------------------")
        print(f"User ID      : {user_id}")
        print(f"Full Name     : {full_name}")
        print(f"Total Images : {len(image_files)}")

        for image in image_files:

            image_path = os.path.join(
                folder_path,
                image
            )

            img = read_image(image_path)

            if img is None:
                print(f"❌ Cannot Read : {image}")
                continue

            try:
                faces = app.get(img)
            except Exception as e:
                print(f"❌ Error processing {image}: {e}")
                continue

            if len(faces) == 0:
                print(f"❌ No Face Found : {image}")
                continue

            embedding = faces[0].embedding
            print(f"✅ Face Found : {image}")
            print(f"Embedding Length : {len(embedding)}")
            save_embedding(user_id, embedding)


# ---------------------------------------
# Main
# ---------------------------------------
def main():

    users = get_users()

    print(f"\nFound {len(users)} users")

    read_user_images(users)


# ---------------------------------------
# Entry Point
# ---------------------------------------
if __name__ == "__main__":
    main()