import os
import numpy as np


def load_embeddings(
    embedding_dir="cache/embeddings"
):

    employee_db = {}

    for employee_id in os.listdir(
        embedding_dir
    ):

        employee_folder = os.path.join(
            embedding_dir,
            employee_id
        )

        embeddings = []

        for file in os.listdir(
            employee_folder
        ):

            if file.endswith(".npy"):

                embedding = np.load(
                    os.path.join(
                        employee_folder,
                        file
                    )
                )

                embeddings.append(
                    embedding
                )

        employee_db[
            employee_id
        ] = embeddings

    return employee_db