import ast
import re
from typing import Any, Dict, Optional
from models import Action, Observation, Reward, StepResult

CODE_TASKS = {
    "easy": {
        "code": '''def calculate_average(numbers):
    total = 0
    for num in numbers
        total += num
    return total / len(numbers)
''',
        "errors": ["missing colon after for loop"],
        "description": "Find syntax errors in this Python function.",
    },
    "medium": {
        "code": '''def find_max(numbers):
    max_val = 0
    for num in numbers:
        if num > max_val:
            max_val = num
    return max_val

def get_user(users, user_id):
    for user in users:
        if user["id"] = user_id:
            return user
    return None

def divide(a, b):
    return a / b
''',
        "bugs": [
            "find_max initializes max_val to 0 — fails for all-negative lists",
            "get_user uses assignment (=) instead of comparison (==)",
            "divide has no zero division guard",
        ],
        "description": "Find all logical bugs in this code and suggest fixes.",
    },
    "hard": {
        "code": '''import sqlite3

def get_user_by_name(name):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    cursor.execute(query)
    return cursor.fetchall()

def render_comment(comment):
    return "<div>" + comment + "</div>"

def login(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        return True
    return False
''',
        "vulnerabilities": [
            {"type": "sql_injection", "location": "get_user_by_name", "description": "String concatenation in SQL query"},
            {"type": "xss", "location": "render_comment", "description": "Unsanitized user input in HTML"},
            {"type": "sql_injection", "location": "login", "description": "f-string SQL query allows injection"},
        ],
        "description": "Identify all security vulnerabilities in this code.",
    },
}


class CodeReviewEnv:
    def __init__(self):
        self.current_task_id: Optional[str] = None
        self.current_obs: Optional[Observation] = None
        self.step_count: int = 0
        self.done: bool = False

    def reset(self, task_id: str) -> Observation:
        self.current_task_id = task_id
        self.step_count = 0
        self.done = False

        if task_id == "code_review_easy":
            task = CODE_TASKS["easy"]
            context = {"code": task["code"]}
            instructions = (
                "Find the syntax error(s) in the provided Python code. "
                "Respond with action payload: {'errors': ['<description of error>']}"
            )
            difficulty = "easy"

        elif task_id == "code_review_medium":
            task = CODE_TASKS["medium"]
            context = {"code": task["code"]}
            instructions = (
                "Identify all logical bugs in the code and suggest fixes for each. "
                "Respond with action payload: {'bugs': [{'location': '<function>', 'issue': '<description>', 'fix': '<suggested fix>'}]}"
            )
            difficulty = "medium"

        else:
            task = CODE_TASKS["hard"]
            context = {"code": task["code"]}
            instructions = (
                "Identify all security vulnerabilities in this code. For each, state the type, location, and recommended fix. "
                "Respond with action payload: {'vulnerabilities': [{'type': '<vuln_type>', 'location': '<function>', 'fix': '<fix>'}]}"
            )
            difficulty = "hard"

        self.current_obs = Observation(
            agent="code_review",
            task_id=task_id,
            difficulty=difficulty,
            context=context,
            instructions=instructions,
            step_count=0,
        )
        return self.current_obs

    def step(self, action: Action) -> StepResult:
        if self.done:
            raise ValueError("Episode done. Call reset() first.")
        self.step_count += 1
        reward = self._grade(action)
        self.done = True
        next_obs = Observation(
            agent="code_review",
            task_id=self.current_task_id,
            difficulty=self.current_obs.difficulty,
            context=self.current_obs.context,
            instructions=self.current_obs.instructions,
            step_count=self.step_count,
        )
        return StepResult(observation=next_obs, reward=reward, done=True, info={})

    def state(self) -> Dict[str, Any]:
        return {
            "task_id": self.current_task_id,
            "step_count": self.step_count,
            "done": self.done,
        }

    def _grade(self, action: Action) -> Reward:
        if self.current_task_id == "code_review_easy":
            return self._grade_easy(action.payload)
        elif self.current_task_id == "code_review_medium":
            return self._grade_medium(action.payload)
        else:
            return self._grade_hard(action.payload)

    def _grade_easy(self, payload: Dict) -> Reward:
        errors = payload.get("errors", [])
        combined = " ".join(errors).lower()
        found = "colon" in combined or "for loop" in combined or "syntax" in combined
        score = 1.0 if found else 0.0
        return Reward(score=score, feedback="Syntax error identified correctly." if found else "Missing or wrong error description.", done=True)

    def _grade_medium(self, payload: Dict) -> Reward:
        bugs = payload.get("bugs", [])
        checks = {
            "max_val_initialization": False,
            "assignment_vs_comparison": False,
            "zero_division": False,
        }
        for bug in bugs:
            text = (str(bug.get("issue", "")) + str(bug.get("location", ""))).lower()
            if any(w in text for w in ["max_val", "negative", "zero", "initialization"]):
                checks["max_val_initialization"] = True
            if any(w in text for w in ["assignment", "==", "comparison", "="]):
                checks["assignment_vs_comparison"] = True
            if any(w in text for w in ["zero", "division", "divide", "zerodivision"]):
                checks["zero_division"] = True

        passed = sum(checks.values())
        score = round(passed / 3, 2)
        return Reward(score=score, partial_credits=checks, feedback=f"{passed}/3 bugs identified.", done=True)

    def _grade_hard(self, payload: Dict) -> Reward:
        vulns = payload.get("vulnerabilities", [])
        checks = {
            "sql_injection_get_user": False,
            "xss_render_comment": False,
            "sql_injection_login": False,
        }
        for v in vulns:
            vtype = str(v.get("type", "")).lower()
            loc = str(v.get("location", "")).lower()
            if "sql" in vtype and "get_user" in loc:
                checks["sql_injection_get_user"] = True
            if "xss" in vtype or ("script" in str(v).lower() and "render" in loc):
                checks["xss_render_comment"] = True
            if "sql" in vtype and "login" in loc:
                checks["sql_injection_login"] = True

        passed = sum(checks.values())
        score = round(passed / 3, 2)
        return Reward(score=score, partial_credits=checks, feedback=f"{passed}/3 vulnerabilities found.", done=True)
