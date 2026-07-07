class Stabilizer:

    def __init__(self, window=3, min_score=0.15):
        self.window = window
        self.min_score = min_score
        self.last_candidate = None
        self.count = 0

    def update(self, emp_id, score=None, min_score=None):
        if emp_id is None or score is None:
            self.last_candidate = None
            self.count = 0
            return None

        threshold = self.min_score if min_score is None else min_score
        if score < threshold:
            self.last_candidate = None
            self.count = 0
            return None

        if self.last_candidate == emp_id:
            self.count += 1
        else:
            self.last_candidate = emp_id
            self.count = 1

        if self.count >= self.window:
            self.count = 0
            return emp_id

        return None
