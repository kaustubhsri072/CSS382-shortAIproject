#!/usr/bin/env python3
"""Study Planner Web App.

A lightweight Flask app to track assignments/exams with priorities and due dates.
Data is stored in a local SQLite database (planner.db).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, url_for

DB_PATH = Path(__file__).parent / "planner.db"

app = Flask(__name__)
app.secret_key = "study-planner-dev-secret"


class PlannerDB:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course TEXT,
                due_date TEXT NOT NULL,
                priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5),
                task_type TEXT NOT NULL,
                notes TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        self.conn.commit()

    def add_task(
        self,
        title: str,
        due_date: str,
        priority: int,
        task_type: str,
        course: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            """
            INSERT INTO tasks (title, course, due_date, priority, task_type, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, course, due_date, priority, task_type, notes, now),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_tasks(self):
        query = """
            SELECT id, title, course, due_date, priority, task_type, notes, completed
            FROM tasks
            ORDER BY completed ASC, due_date ASC, priority DESC, id ASC
        """
        return self.conn.execute(query).fetchall()

    def mark_done(self, task_id: int) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            """
            UPDATE tasks
            SET completed = 1, completed_at = ?
            WHERE id = ? AND completed = 0
            """,
            (now, task_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def undo_done(self, task_id: int) -> bool:
        cursor = self.conn.execute(
            """
            UPDATE tasks
            SET completed = 0, completed_at = NULL
            WHERE id = ? AND completed = 1
            """,
            (task_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        cursor = self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed = self.conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1").fetchone()[0]
        pending = total - completed
        overdue = self.conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 0 AND due_date < ?",
            (date.today().isoformat(),),
        ).fetchone()[0]
        due_soon = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM tasks
            WHERE completed = 0
              AND due_date BETWEEN ? AND date(?, '+7 day')
            """,
            (date.today().isoformat(), date.today().isoformat()),
        ).fetchone()[0]

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "due_soon": due_soon,
        }

    def close(self) -> None:
        self.conn.close()


def validate_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def priority_label(n: int) -> str:
    return {
        1: "Very Low",
        2: "Low",
        3: "Medium",
        4: "High",
        5: "Critical",
    }[n]


def due_status(due_date_str: str, completed: int) -> str:
    if completed:
        return "Done"

    due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    delta = (due - date.today()).days
    if delta < 0:
        return f"Overdue by {-delta}d"
    if delta == 0:
        return "Due Today"
    if delta <= 7:
        return f"Due in {delta}d"
    return "Upcoming"


@app.get("/")
def index():
    db = PlannerDB()
    try:
        tasks = db.list_tasks()
        pending_tasks = [task for task in tasks if not task["completed"]]
        completed_tasks = [task for task in tasks if task["completed"]]
        return render_template(
            "index.html",
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            stats=db.stats(),
            due_status=due_status,
            priority_label=priority_label,
            today=date.today().isoformat(),
        )
    finally:
        db.close()


@app.post("/add")
def add_task():
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip()
    task_type = request.form.get("task_type", "assignment").strip().lower()
    course = request.form.get("course", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    raw_priority = request.form.get("priority", "3").strip()
    try:
        priority = int(raw_priority)
    except ValueError:
        flash("Priority must be a number from 1 to 5.", "error")
        return redirect(url_for("index"))

    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("index"))
    if not validate_date(due_date):
        flash("Due date must be in YYYY-MM-DD format.", "error")
        return redirect(url_for("index"))
    if priority < 1 or priority > 5:
        flash("Priority must be between 1 and 5.", "error")
        return redirect(url_for("index"))

    allowed_types = {"assignment", "exam", "project", "reading", "other"}
    if task_type not in allowed_types:
        task_type = "other"

    db = PlannerDB()
    try:
        db.add_task(
            title=title,
            due_date=due_date,
            priority=priority,
            task_type=task_type,
            course=course,
            notes=notes,
        )
        flash("Task added.", "success")
    finally:
        db.close()

    return redirect(url_for("index"))


@app.post("/done/<int:task_id>")
def done_task(task_id: int):
    db = PlannerDB()
    try:
        updated = db.mark_done(task_id)
        flash("Task marked complete." if updated else "Task already completed or missing.", "success" if updated else "error")
    finally:
        db.close()
    return redirect(url_for("index"))


@app.post("/undo/<int:task_id>")
def undo_task(task_id: int):
    db = PlannerDB()
    try:
        updated = db.undo_done(task_id)
        flash("Task moved back to pending." if updated else "Task not found.", "success" if updated else "error")
    finally:
        db.close()
    return redirect(url_for("index"))


@app.post("/delete/<int:task_id>")
def delete_task(task_id: int):
    db = PlannerDB()
    try:
        deleted = db.delete_task(task_id)
        flash("Task deleted." if deleted else "Task not found.", "success" if deleted else "error")
    finally:
        db.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
