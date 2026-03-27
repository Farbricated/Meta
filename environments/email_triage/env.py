import random
from typing import Any, Dict, Optional, Tuple
from models import Action, Observation, Reward, StepResult

EMAILS = {
    "easy": [
        {
            "id": "e1",
            "subject": "You won $1,000,000!!!",
            "sender": "promo@totally-legit-lottery.com",
            "body": "Click here to claim your prize now! Limited time offer!",
            "label": "spam",
        },
        {
            "id": "e2",
            "subject": "Q3 Budget Review Meeting — Urgent",
            "sender": "cfo@company.com",
            "body": "Please review the attached Q3 budget before our meeting tomorrow at 9 AM.",
            "label": "important",
        },
        {
            "id": "e3",
            "subject": "Your weekly digest from Medium",
            "sender": "noreply@medium.com",
            "body": "Top stories this week: AI trends, productivity hacks, and more.",
            "label": "newsletter",
        },
    ],
    "medium": {
        "emails": [
            {"id": "m1", "subject": "Server is DOWN", "sender": "ops@company.com", "body": "Production server unresponsive since 2 AM. All hands needed.", "priority": 1, "category": "critical"},
            {"id": "m2", "subject": "Team lunch tomorrow?", "sender": "colleague@company.com", "body": "Hey, want to grab lunch tomorrow at noon?", "priority": 5, "category": "social"},
            {"id": "m3", "subject": "Client contract renewal due Friday", "sender": "sales@company.com", "body": "Acme Corp contract expires Friday. Need approval ASAP.", "priority": 2, "category": "business"},
            {"id": "m4", "subject": "Weekly newsletter", "sender": "news@techdigest.com", "body": "This week in tech...", "priority": 8, "category": "newsletter"},
            {"id": "m5", "subject": "Security breach detected", "sender": "security@company.com", "body": "Unusual login attempts detected on your account.", "priority": 1, "category": "critical"},
            {"id": "m6", "subject": "Invoice #4521 due", "sender": "billing@vendor.com", "body": "Invoice of $5,400 due in 3 days.", "priority": 3, "category": "finance"},
            {"id": "m7", "subject": "Happy Birthday!", "sender": "hr@company.com", "body": "Wishing you a wonderful birthday!", "priority": 9, "category": "social"},
            {"id": "m8", "subject": "Product launch presentation review", "sender": "marketing@company.com", "body": "Please review slides before Thursday's launch meeting.", "priority": 3, "category": "business"},
            {"id": "m9", "subject": "Free webinar: Boost productivity", "sender": "promo@webinar.com", "body": "Register now for our free webinar!", "priority": 10, "category": "newsletter"},
            {"id": "m10", "subject": "Urgent: Legal document needs signature", "sender": "legal@company.com", "body": "Contract must be signed by EOD today.", "priority": 2, "category": "legal"},
        ]
    },
    "hard": {
        "email": {
            "id": "h1",
            "subject": "Extremely disappointed — Order #78234",
            "sender": "angry.customer@email.com",
            "body": (
                "I have been a loyal customer for 5 years and I am absolutely furious. "
                "My order #78234 arrived broken for the SECOND time this month. "
                "Your customer service team has been dismissive and unhelpful. "
                "I demand a full refund, a replacement, AND compensation for the inconvenience. "
                "If this is not resolved within 24 hours, I will be filing a complaint with "
                "the consumer court and leaving reviews on every platform I can find."
            ),
            "expected_elements": [
                "acknowledge_frustration",
                "apologize",
                "offer_refund",
                "offer_replacement",
                "provide_timeline",
                "professional_tone",
            ],
        }
    },
}


class EmailTriageEnv:
    def __init__(self):
        self.current_task_id: Optional[str] = None
        self.current_obs: Optional[Observation] = None
        self.step_count: int = 0
        self.done: bool = False

    def reset(self, task_id: str) -> Observation:
        self.current_task_id = task_id
        self.step_count = 0
        self.done = False

        if task_id == "email_triage_easy":
            email = random.choice(EMAILS["easy"])
            context = {"email": email}
            instructions = (
                "Classify the following email as one of: 'spam', 'important', or 'newsletter'. "
                "Respond with action payload: {'classification': '<label>'}"
            )
            difficulty = "easy"

        elif task_id == "email_triage_medium":
            context = {"emails": EMAILS["medium"]["emails"]}
            instructions = (
                "Prioritize the 10 emails from most urgent (1) to least urgent (10). "
                "Respond with action payload: {'order': [<email_id_list_sorted_by_priority>]}"
            )
            difficulty = "medium"

        else:
            context = {"email": EMAILS["hard"]["email"]}
            instructions = (
                "Draft a professional and empathetic reply to this customer complaint email. "
                "Your reply should acknowledge their frustration, apologize, offer refund and replacement, "
                "and provide a resolution timeline. "
                "Respond with action payload: {'reply': '<your drafted reply>'}"
            )
            difficulty = "hard"

        self.current_obs = Observation(
            agent="email_triage",
            task_id=task_id,
            difficulty=difficulty,
            context=context,
            instructions=instructions,
            step_count=0,
        )
        return self.current_obs

    def step(self, action: Action) -> StepResult:
        if self.done:
            raise ValueError("Episode is done. Call reset() first.")

        self.step_count += 1
        reward = self._grade(action)
        self.done = True

        next_obs = Observation(
            agent="email_triage",
            task_id=self.current_task_id,
            difficulty=self.current_obs.difficulty,
            context=self.current_obs.context,
            instructions=self.current_obs.instructions,
            step_count=self.step_count,
        )
        return StepResult(observation=next_obs, reward=reward, done=self.done, info={})

    def state(self) -> Dict[str, Any]:
        return {
            "task_id": self.current_task_id,
            "step_count": self.step_count,
            "done": self.done,
            "current_observation": self.current_obs.dict() if self.current_obs else None,
        }

    def _grade(self, action: Action) -> Reward:
        task_id = self.current_task_id
        payload = action.payload

        if task_id == "email_triage_easy":
            return self._grade_easy(payload)
        elif task_id == "email_triage_medium":
            return self._grade_medium(payload)
        else:
            return self._grade_hard(payload)

    def _grade_easy(self, payload: Dict) -> Reward:
        correct_label = self.current_obs.context["email"]["label"]
        given = payload.get("classification", "").strip().lower()
        if given == correct_label:
            return Reward(score=1.0, feedback="Correct classification!", done=True)
        elif given in ["spam", "important", "newsletter"]:
            return Reward(score=0.0, feedback=f"Incorrect. Expected '{correct_label}', got '{given}'.", done=True)
        else:
            return Reward(score=0.0, feedback="Invalid classification label.", done=True)

    def _grade_medium(self, payload: Dict) -> Reward:
        order = payload.get("order", [])
        emails = EMAILS["medium"]["emails"]
        correct_order = sorted(emails, key=lambda e: e["priority"])
        correct_ids = [e["id"] for e in correct_order]

        if not order:
            return Reward(score=0.0, feedback="No order provided.", done=True)

        score = 0.0
        feedback_parts = []
        top3_correct = order[:3] == correct_ids[:3]
        top5_correct = order[:5] == correct_ids[:5]
        all_correct = order == correct_ids

        if all_correct:
            score = 1.0
            feedback_parts.append("Perfect prioritization!")
        elif top5_correct:
            score = 0.75
            feedback_parts.append("Top 5 correctly prioritized.")
        elif top3_correct:
            score = 0.5
            feedback_parts.append("Top 3 critical emails correctly prioritized.")
        else:
            # partial: check how many are in right position
            correct_positions = sum(1 for i, eid in enumerate(order) if i < len(correct_ids) and eid == correct_ids[i])
            score = round(correct_positions / 10, 2)
            feedback_parts.append(f"{correct_positions}/10 emails in correct position.")

        return Reward(score=score, partial_credits={"order_accuracy": score}, feedback=" ".join(feedback_parts), done=True)

    def _grade_hard(self, payload: Dict) -> Reward:
        reply = payload.get("reply", "").lower()
        expected = EMAILS["hard"]["email"]["expected_elements"]
        checks = {
            "acknowledge_frustration": any(w in reply for w in ["understand", "frustrat", "disappoint", "concern"]),
            "apologize": any(w in reply for w in ["sorry", "apologize", "apology", "sincerely apologize"]),
            "offer_refund": any(w in reply for w in ["refund", "full refund", "money back"]),
            "offer_replacement": any(w in reply for w in ["replacement", "replace", "new order", "send another"]),
            "provide_timeline": any(w in reply for w in ["24 hours", "within", "by", "today", "tomorrow", "48 hours"]),
            "professional_tone": len(reply) > 100 and not any(w in reply for w in ["whatever", "not my problem", "too bad"]),
        }
        passed = sum(checks.values())
        score = round(passed / len(expected), 2)
        missing = [k for k, v in checks.items() if not v]
        feedback = f"Score: {passed}/{len(expected)} elements present."
        if missing:
            feedback += f" Missing: {', '.join(missing)}."
        return Reward(score=score, partial_credits=checks, feedback=feedback, done=True)
