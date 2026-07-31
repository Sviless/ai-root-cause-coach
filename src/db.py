"""SQLite storage for saved root cause analyses and dashboard metrics."""

import os
import json
import sqlite3

from src.utils import now_iso

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "root_cause_coach.db")


def get_connection(db_path=DB_PATH):
    """Open a SQLite connection, creating the data folder if needed."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    """Create the analyses table if it does not exist."""
    conn = get_connection(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            title TEXT,
            category TEXT,
            confidence_score INTEGER,
            confidence_status TEXT,
            maturity_score INTEGER,
            maturity_status TEXT,
            recurrence_level TEXT,
            recurrence_score INTEGER,
            open_action_items INTEGER,
            inputs_json TEXT,
            package_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_analysis(package, db_path=DB_PATH):
    """Persist a generated package. Returns the new row id."""
    conf = package.get("confidence", {})
    mat = package.get("maturity", {})
    rec = package.get("recurrence", {})
    open_items = sum(
        1
        for a in package.get("action_items", [])
        if a.get("Status", "").lower() != "closed"
    )

    conn = get_connection(db_path)
    cursor = conn.execute(
        """
        INSERT INTO analyses (
            created_at, title, category,
            confidence_score, confidence_status,
            maturity_score, maturity_status,
            recurrence_level, recurrence_score,
            open_action_items, inputs_json, package_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            package.get("created_at", now_iso()),
            package.get("title", "Untitled"),
            package.get("category", "Other"),
            conf.get("score", 0),
            conf.get("status", ""),
            mat.get("score", 0),
            mat.get("status", ""),
            rec.get("level", "Low"),
            rec.get("score", 0),
            open_items,
            json.dumps(package.get("inputs", {})),
            json.dumps(package),
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def _row_to_dict(row):
    data = dict(row)
    try:
        data["package"] = json.loads(data.get("package_json") or "{}")
    except json.JSONDecodeError:
        data["package"] = {}
    return data


def get_all_analyses(db_path=DB_PATH):
    """Return all saved analyses (newest first) with parsed packages."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM analyses ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_analysis(analysis_id, db_path=DB_PATH):
    """Return a single analysis by id, or None."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def delete_analysis(analysis_id, db_path=DB_PATH):
    """Delete an analysis by id."""
    conn = get_connection(db_path)
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()


def get_dashboard_metrics(db_path=DB_PATH):
    """Aggregate saved analyses into dashboard-ready metrics."""
    analyses = get_all_analyses(db_path)
    total = len(analyses)

    if total == 0:
        return {
            "total": 0,
            "avg_confidence": 0,
            "avg_maturity": 0,
            "high_recurrence_count": 0,
            "open_action_items": 0,
            "by_category": {},
            "common_causes": {},
        }

    avg_conf = round(sum(a["confidence_score"] for a in analyses) / total, 1)
    avg_mat = round(sum(a["maturity_score"] for a in analyses) / total, 1)
    high_rec = sum(1 for a in analyses if a["recurrence_level"] == "High")
    open_items = sum((a["open_action_items"] or 0) for a in analyses)

    by_category = {}
    common_causes = {}
    for a in analyses:
        by_category[a["category"]] = by_category.get(a["category"], 0) + 1
        # Count fishbone categories that produced more than the base hint.
        fishbone = a["package"].get("fishbone", {})
        for cat, causes in fishbone.items():
            if len(causes) > 1:
                common_causes[cat] = common_causes.get(cat, 0) + 1

    return {
        "total": total,
        "avg_confidence": avg_conf,
        "avg_maturity": avg_mat,
        "high_recurrence_count": high_rec,
        "open_action_items": open_items,
        "by_category": by_category,
        "common_causes": common_causes,
    }
