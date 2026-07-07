import json
import os

import numpy as np

from PSqlConnector import get_conn


def _coerce_embedding(value):
    if value is None:
        return None

    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            pass

    if isinstance(value, np.ndarray):
        return value.astype(np.float32)

    if isinstance(value, (list, tuple)):
        return np.asarray(value, dtype=np.float32)

    return np.asarray(value, dtype=np.float32)


def load_embeddings(path="cache/embeddings"):
    db = {}

    for emp in os.listdir(path):
        folder = os.path.join(path, emp)

        if not os.path.isdir(folder):
            continue

        embs = []

        for f in os.listdir(folder):
            if f.endswith(".npy"):
                embs.append(np.load(os.path.join(folder, f)))

        db[emp] = embs

    return db


def load_embeddings_from_db():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.full_name,
                    u.empcode,
                    uf.embedding
                FROM public.user_face_embeddings AS uf
                JOIN public.users AS u ON u.user_id = uf.user_id
                WHERE uf.is_active = TRUE
                  AND uf.embedding IS NOT NULL
                  AND uf.model_name = %s
                ORDER BY u.user_id, uf.embedding_id
                """,
                ("buffalo_l",),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    employee_db = {}
    employee_meta = {}

    for row in rows:
        user_id = row[0]
        embedding = _coerce_embedding(row[3])
        if embedding is None or embedding.size == 0:
            continue

        employee_db.setdefault(user_id, []).append(embedding)
        employee_meta[user_id] = {
            "user_id": user_id,
            "full_name": row[1],
            "empcode": row[2],
        }

    return employee_db, employee_meta