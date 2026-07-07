import json
import os
from datetime import datetime

from PSqlConnector import get_conn


class AttendanceEngine:
    def __init__(self, conn=None):
        os.makedirs("events", exist_ok=True)
        self.conn = conn or get_conn()
        self.checked_in = set()

    def create_event(
        self,
        emp_id=None,
        camera_id="CAM1",
        confidence=0.0,
        timestamp=None,
        user_id=None,
        event_type="CHECKIN",
        notes=None,
        status="CREATED",
    ):
        dedupe_key = (user_id if user_id is not None else "UNKNOWN", str(timestamp))
        if dedupe_key in self.checked_in:
            return None

        self.checked_in.add(dedupe_key)

        if timestamp is None:
            timestamp_value = datetime.now()
        elif isinstance(timestamp, datetime):
            timestamp_value = timestamp
        else:
            timestamp_value = timestamp

        if self.conn is not None:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.attendance_event
                        (camera_id, confidence_score, user_id, event_timestamp, event_type, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        camera_id,
                        round(float(confidence), 2),
                        user_id,
                        timestamp_value,
                        event_type,
                        notes,
                        status,
                    ),
                )
            self.conn.commit()

        event = {
            "employee_id": emp_id,
            "user_id": user_id,
            "camera_id": camera_id,
            "event_type": event_type,
            "confidence": round(confidence, 3),
            "timestamp": str(timestamp_value),
            "notes": notes,
            "status": status,
        }

        file_name = str(user_id) if user_id is not None else "unknown"
        with open(f"events/{file_name}.json", "w") as f:
            json.dump(event, f, indent=4)

        return event

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None