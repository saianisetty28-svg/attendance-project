import numpy as np

EPS = 1e-10


def cosine_similarity(a, b):
    """Return cosine similarity between two vectors.

    Both inputs are converted to NumPy arrays and normalized safely.
    If either vector has near-zero norm, this returns 0.0 instead of NaN.
    """
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < EPS or norm_b < EPS:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def find_best_match(embedding, employee_db, threshold=0.55):
    """Find the employee with the highest cosine similarity.

    Arguments:
    - embedding: query face embedding vector
    - employee_db: dict mapping employee IDs to lists of stored embeddings
    - threshold: minimum similarity required to accept a match

    Returns:
    - (employee_id, score) if best score >= threshold
    - (None, best_score) otherwise
    """
    embedding = np.asarray(embedding, dtype=np.float32)
    if embedding.size == 0 or np.linalg.norm(embedding) < EPS:
        return None, 0.0

    best_score = 0.0
    best_emp = None

    for emp_id, emb_list in employee_db.items():
        # Allow either a list of embeddings or a single embedding value
        candidates = emb_list if isinstance(emb_list, (list, tuple, np.ndarray)) else [emb_list]

        for emb in candidates:
            score = cosine_similarity(embedding, emb)
            if score > best_score:
                best_score = score
                best_emp = emp_id

    if best_score >= threshold:
        return best_emp, best_score

    return None, best_score


if __name__ == "__main__":
    import numpy as np

    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    employees = {
        "EMP100": [np.array([1.0, 0.0, 0.0], dtype=np.float32)],
        "EMP101": [np.array([0.5, 0.5, 0.0], dtype=np.float32)],
    }

    print("match result:", find_best_match(query, employees, threshold=0.5))
    print("zero vector result:", find_best_match(np.zeros(3), employees))

