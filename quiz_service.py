import random
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from services.mongo_client import get_db
from models.quiz import Quiz, QuizQuestion, QuizSession


class QuizService:
    def __init__(self):
        self.db = get_db()
        self.col_quizzes = self.db["quizzes"]
        self.col_sessions = self.db["quiz_sessions"]

    # Quiz CRUD
    def create_quiz(self, quiz: Quiz) -> str:
        quiz.validate()
        self.col_quizzes.insert_one(quiz.to_dict())
        return quiz.quizId or ""

    def get_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        return self.col_quizzes.find_one({"quizId": quiz_id}, {"_id": 0})

    def list_quizzes_by_owner(self, owner_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.col_quizzes.find({"ownerId": owner_id}, {"_id": 0}).sort("createdAt", -1).limit(limit))

    # Session lifecycle
    def _generate_session_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _compute_question_order(self, quiz: Dict[str, Any]) -> List[int]:
        order = list(range(len(quiz.get("questions", []))))
        if quiz.get("shuffleQuestions"):
            random.shuffle(order)
        return order

    def start_session(self, quiz_id: str, chat_id: int, is_group: bool, started_by: int) -> Dict[str, Any]:
        quiz = self.get_quiz(quiz_id)
        if not quiz:
            raise ValueError("Quiz not found")
        # prevent concurrent session in same chat for same quiz
        existing = self.col_sessions.find_one({
            "quizId": quiz_id,
            "chatId": chat_id,
            "status": {"$in": ["pending", "running"]}
        })
        if existing:
            return existing
        session_id = self._generate_session_id()
        question_order = self._compute_question_order(quiz)
        negative = float(quiz.get("negativeMarking") or 0.0)
        total_seconds = quiz.get("totalSeconds")
        ends_at = None
        if isinstance(total_seconds, int) and total_seconds > 0:
            ends_at = datetime.utcnow() + timedelta(seconds=total_seconds)
        session = QuizSession(
            sessionId=session_id,
            quizId=quiz_id,
            chatId=chat_id,
            isGroup=is_group,
            startedBy=started_by,
            questionOrder=question_order,
            negativeMarking=negative,
            endsAt=ends_at,
            status="pending"
        )
        self.col_sessions.insert_one(session.to_dict())
        return session.to_dict()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.col_sessions.find_one({"sessionId": session_id}, {"_id": 0})

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        self.col_sessions.update_one({"sessionId": session_id}, {"$set": updates})

    def activate_session(self, session_id: str) -> None:
        self.col_sessions.update_one(
            {"sessionId": session_id},
            {"$set": {"status": "running", "startedAt": datetime.utcnow()}}
        )

    def map_poll(self, session_id: str, poll_id: str, q_index: int) -> None:
        self.col_sessions.update_one({"sessionId": session_id}, {"$set": {f"pollIdToQuestionIndex.{poll_id}": q_index}})

    def record_answer(self, session_id: str, user_id: int, q_index: int, selected_index: int,
                      correct_index: int, negative_marking: float, user_info: Optional[Dict[str, Any]] = None) -> float:
        # compute incremental score
        delta = 0.0
        if selected_index == correct_index:
            delta = 1.0
        else:
            if negative_marking > 0:
                delta = -negative_marking
        # atomically update
        sess = self.get_session(session_id)
        if not sess:
            return 0.0
        user_key = str(user_id)
        prev = float(sess.get("scores", {}).get(user_key, 0.0))
        new_score = prev + delta
        updates: Dict[str, Any] = {
            f"answers.{user_key}.{q_index}": selected_index,
            f"scores.{user_key}": new_score
        }
        if user_info:
            display = user_info.get("display")
            if display:
                updates[f"displayNames.{user_key}"] = display
            username = user_info.get("username")
            if username:
                updates[f"displayUsernames.{user_key}"] = username
        self.col_sessions.update_one(
            {"sessionId": session_id},
            {"$set": updates}
        )
        return new_score

    def end_session(self, session_id: str) -> Dict[str, Any]:
        self.update_session(session_id, {"status": "ended", "endsAt": datetime.utcnow()})
        sess = self.get_session(session_id) or {}
        return sess

    # Helpers
    def get_question_by_index(self, quiz: Dict[str, Any], index: int) -> Tuple[str, List[str], int]:
        q = quiz["questions"][index]
        text = q["text"]
        options = list(q["options"])
        correct = int(q["correctIndex"])
        if quiz.get("shuffleOptions"):
            enumerated = list(enumerate(options))
            random.shuffle(enumerated)
            new_options = [opt for _, opt in enumerated]
            index_map = {new_idx: old_idx for new_idx, (old_idx, _) in enumerate(enumerated)}
            # translate correct to new index
            new_correct = None
            for new_idx, old_idx in index_map.items():
                if old_idx == correct:
                    new_correct = new_idx
                    break
            return text, new_options, int(new_correct if new_correct is not None else correct)
        return text, options, correct


quiz_service = QuizService()


