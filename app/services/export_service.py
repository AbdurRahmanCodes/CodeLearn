"""CSV export shaping logic used by web route handlers."""

import csv
import io
from typing import Dict, Iterable, List


class ExportService:
    """Builds export-ready rows and CSV payloads."""

    @staticmethod
    def _iso_timestamp(value):
        return value.isoformat() if value else ""

    @staticmethod
    def build_research_dataset_rows(rows: Iterable[Dict]) -> List[Dict]:
        normalized = []
        for row in rows:
            cleaned = {k: v for k, v in row.items() if k != "_id"}
            if "timestamp" in cleaned:
                cleaned["timestamp"] = ExportService._iso_timestamp(cleaned.get("timestamp"))
            normalized.append(cleaned)
        return normalized

    @staticmethod
    def build_session_summary_rows(rows: Iterable[Dict]) -> List[Dict]:
        per_session = {}
        for row in rows:
            sid = row.get("session_id")
            if sid not in per_session:
                per_session[sid] = {
                    "session_id": sid,
                    "group_type": row.get("group_type"),
                    "experiment_group": row.get("experiment_group"),
                    "attempts": 0,
                    "passes": 0,
                }
            per_session[sid]["attempts"] += 1
            if row.get("result") == "pass":
                per_session[sid]["passes"] += 1
        return list(per_session.values())

    @staticmethod
    def build_quiz_rows(rows: Iterable[Dict]) -> List[Dict]:
        normalized = []
        for row in rows:
            normalized.append({
                "session_id": row.get("session_id"),
                "group_type": row.get("group_type"),
                "experiment_group": row.get("experiment_group"),
                "topic": row.get("topic"),
                "score": row.get("score"),
                "total_questions": row.get("total_questions"),
                "score_pct": row.get("score_pct"),
                "timestamp": ExportService._iso_timestamp(row.get("timestamp")),
            })
        return normalized

    @staticmethod
    def build_recommendation_rows(rows: Iterable[Dict]) -> List[Dict]:
        normalized = []
        for row in rows:
            normalized.append({
                "session_id": row.get("session_id"),
                "group_type": row.get("group_type"),
                "experiment_group": row.get("experiment_group"),
                "exercise_id": row.get("exercise_id"),
                "topic": row.get("topic"),
                "recommendation_type": row.get("recommendation_type"),
                "title": row.get("title"),
                "reason": row.get("reason"),
                "resource_url": row.get("resource_url"),
                "timestamp": ExportService._iso_timestamp(row.get("timestamp")),
            })
        return normalized

    @staticmethod
    def to_csv_bytes(rows: List[Dict]) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")
