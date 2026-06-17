import os
import cv2
import numpy as np

from insightface.app import FaceAnalysis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "cache", "employee_images")
EMBEDDING_DIR = os.path.join(BASE_DIR, "cache", "embeddings")

app = FaceAnalysis(
    name="buffalo_l"
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

def generate_embeddings():

    os.makedirs(
        EMBEDDING_DIR,
        exist_ok=True
    )

    employees = os.listdir(
        IMAGE_DIR
    )

    for employee_id in employees:

        employee_folder = os.path.join(
            IMAGE_DIR,
            employee_id
        )

        output_folder = os.path.join(
            EMBEDDING_DIR,
            employee_id
        )

        os.makedirs(
            output_folder,
            exist_ok=True
        )

        image_files = os.listdir(
            employee_folder
        )

        emb_count = 1

        for image_file in image_files:

            image_path = os.path.join(
                employee_folder,
                image_file
            )

            img = cv2.imread(image_path)

            if img is None:
                continue

            faces = app.get(img)

            if len(faces) == 0:
                continue

            embedding = (
                faces[0].embedding
            )

            np.save(
                os.path.join(
                    output_folder,
                    f"emb{emb_count}.npy"
                ),
                embedding
            )

            emb_count += 1

        print(
            f"Embeddings created: {employee_id}"
        )


if __name__ == "__main__":
    generate_embeddings()