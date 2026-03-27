from typing import Any, Dict, Optional
from models import Action, Observation, Reward, StepResult

DATASETS = {
    "easy": {
        "data": [
            {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "age": None, "email": "bob@example.com"},
            {"id": 3, "name": "Alice", "age": 30, "email": "alice@example.com"},  # duplicate
            {"id": 4, "name": None, "age": 25, "email": "charlie@example.com"},
            {"id": 5, "name": "Dave", "age": 40, "email": None},
        ],
        "missing_fields": ["age (row 2)", "name (row 4)", "email (row 5)"],
        "duplicate_rows": [1, 3],  # 1-indexed
    },
    "medium": {
        "data": [
            {"id": 1, "name": "Alice", "age": "thirty", "salary": "50000", "join_date": "2020/01/15"},
            {"id": 2, "name": "Bob", "age": 25, "salary": "$60,000", "join_date": "15-03-2021"},
            {"id": 3, "name": "Charlie", "age": "28", "salary": "70000", "join_date": "2019-07-22"},
            {"id": 4, "name": "dave", "age": 35, "salary": "80,000", "join_date": "2022/11/01"},
        ],
        "issues": {
            "age": "row 1 has string 'thirty' instead of integer",
            "salary": "inconsistent formats ($60,000 and 80,000 with comma)",
            "join_date": "inconsistent date formats (YYYY/MM/DD, DD-MM-YYYY, YYYY-MM-DD)",
            "name": "row 4 'dave' not capitalized",
        },
    },
    "hard": {
        "data": [
            {"id": 1, "value": 10.5},
            {"id": 2, "value": 11.2},
            {"id": 3, "value": 10.8},
            {"id": 4, "value": 999.0},  # outlier
            {"id": 5, "value": 10.1},
            {"id": 6, "value": None},   # missing
            {"id": 7, "value": 11.5},
            {"id": 8, "value": -500.0}, # outlier
            {"id": 9, "value": 10.9},
            {"id": 10, "value": 11.0},
        ],
        "outliers": [4, 8],
        "missing": [6],
        "expected_imputed_value_range": (10.0, 12.0),
    },
}


class DataCleaningEnv:
    def __init__(self):
        self.current_task_id: Optional[str] = None
        self.current_obs: Optional[Observation] = None
        self.step_count: int = 0
        self.done: bool = False

    def reset(self, task_id: str) -> Observation:
        self.current_task_id = task_id
        self.step_count = 0
        self.done = False

        if task_id == "data_cleaning_easy":
            task = DATASETS["easy"]
            context = {"data": task["data"]}
            instructions = (
                "Identify all missing values (null fields) and exact duplicate rows in the dataset. "
                "Respond with action payload: {'missing': ['<field> (row <n>)'], 'duplicates': [<row_ids>]}"
            )
            difficulty = "easy"

        elif task_id == "data_cleaning_medium":
            task = DATASETS["medium"]
            context = {"data": task["data"]}
            instructions = (
                "Identify all data type issues and inconsistencies, and provide the corrected dataset. "
                "Respond with action payload: {'issues': {'<field>': '<description>'}, 'cleaned_data': [<corrected rows>]}"
            )
            difficulty = "medium"

        else:
            task = DATASETS["hard"]
            context = {"data": task["data"]}
            instructions = (
                "Detect outliers (using IQR or z-score), identify missing values, and provide the cleaned dataset "
                "with outliers replaced and missing values imputed using the mean of non-outlier values. "
                "Respond with action payload: {'outliers': [<row ids>], 'missing': [<row ids>], 'cleaned_data': [<rows>]}"
            )
            difficulty = "hard"

        self.current_obs = Observation(
            agent="data_cleaning",
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
            agent="data_cleaning",
            task_id=self.current_task_id,
            difficulty=self.current_obs.difficulty,
            context=self.current_obs.context,
            instructions=self.current_obs.instructions,
            step_count=self.step_count,
        )
        return StepResult(observation=next_obs, reward=reward, done=True, info={})

    def state(self) -> Dict[str, Any]:
        return {"task_id": self.current_task_id, "step_count": self.step_count, "done": self.done}

    def _grade(self, action: Action) -> Reward:
        if self.current_task_id == "data_cleaning_easy":
            return self._grade_easy(action.payload)
        elif self.current_task_id == "data_cleaning_medium":
            return self._grade_medium(action.payload)
        else:
            return self._grade_hard(action.payload)

    def _grade_easy(self, payload: Dict) -> Reward:
        missing = [str(m).lower() for m in payload.get("missing", [])]
        duplicates = payload.get("duplicates", [])

        missing_checks = {
            "age_row2": any("age" in m and ("2" in m or "row 2" in m) for m in missing),
            "name_row4": any("name" in m and ("4" in m or "row 4" in m) for m in missing),
            "email_row5": any("email" in m and ("5" in m or "row 5" in m) for m in missing),
        }
        dup_check = set(duplicates) == {1, 3} or set(str(d) for d in duplicates) == {"1", "3"}

        passed_missing = sum(missing_checks.values())
        score = round((passed_missing / 3 * 0.7) + (0.3 if dup_check else 0.0), 2)
        feedback = f"Missing fields: {passed_missing}/3 found. Duplicates: {'correct' if dup_check else 'incorrect'}."
        return Reward(score=score, partial_credits={**missing_checks, "duplicates": dup_check}, feedback=feedback, done=True)

    def _grade_medium(self, payload: Dict) -> Reward:
        issues = {k.lower(): str(v).lower() for k, v in payload.get("issues", {}).items()}
        cleaned = payload.get("cleaned_data", [])
        checks = {
            "age_type": "age" in issues and any(w in issues["age"] for w in ["string", "integer", "int", "thirty"]),
            "salary_format": "salary" in issues and any(w in issues["salary"] for w in ["format", "comma", "inconsistent", "$"]),
            "date_format": "join_date" in issues and any(w in issues["join_date"] for w in ["format", "inconsistent", "date"]),
            "name_case": "name" in issues and any(w in issues["name"] for w in ["capital", "case", "dave", "lower"]),
            "data_cleaned": len(cleaned) == 4,
        }
        passed = sum(checks.values())
        score = round(passed / 5, 2)
        return Reward(score=score, partial_credits=checks, feedback=f"{passed}/5 data quality checks passed.", done=True)

    def _grade_hard(self, payload: Dict) -> Reward:
        outliers = set(int(x) for x in payload.get("outliers", []))
        missing = set(int(x) for x in payload.get("missing", []))
        cleaned = payload.get("cleaned_data", [])

        outlier_correct = outliers == {4, 8}
        missing_correct = missing == {6}

        imputed_ok = False
        if cleaned:
            row6 = next((r for r in cleaned if r.get("id") == 6), None)
            lo, hi = DATASETS["hard"]["expected_imputed_value_range"]
            if row6 and row6.get("value") is not None:
                imputed_ok = lo <= float(row6["value"]) <= hi

        checks = {
            "outliers_detected": outlier_correct,
            "missing_detected": missing_correct,
            "imputation_correct": imputed_ok,
        }
        passed = sum(checks.values())
        score = round(passed / 3, 2)
        return Reward(score=score, partial_credits=checks, feedback=f"{passed}/3 data quality operations correct.", done=True)
