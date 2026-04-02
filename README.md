# Study Planner (Python Web App)

## Project Info
- NetID: kausri72
- Name: Kaustubh Srikantapuram
- GitHub Repository: https://github.com/kaustubhsri072/CSS382-shortAIproject
- Deployed Site: Local Host

## Idea
A simple Flask web app to track assignments, exams, projects, and deadlines.

## Features
- Add tasks with due date, priority, course, type, and notes
- Mark tasks as completed, undo completion, or delete
- Dashboard cards for total/pending/completed/overdue/due-soon tasks
- Clean browser UI with forms and task tables

## Requirements
- Python 3.9+

## Run
From this project folder:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open: http://127.0.0.1:5000

## Data Storage
Tasks are stored locally in `planner.db` (SQLite).
