from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


def _short_id_from_title(title: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9]+', '-', title).strip('-').lower()
    base = base[:24] if base else 'quiz'
    ts = hex(int(datetime.utcnow().timestamp()))[2:]
    return f"{base}-{ts}"[:32]


@dataclass
class QuizQuestion:
    text: str
    options: List[str]
    correctIndex: int
    explanation: Optional[str] = None

    def validate(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Question text is required")
        if not isinstance(self.options, list) or len(self.options) < 2:
            raise ValueError("At least 2 options are required")
        if any(not isinstance(o, str) or not o.strip() for o in self.options):
            raise ValueError("Options must be non-empty strings")
        if not isinstance(self.correctIndex, int) or not (0 <= self.correctIndex < len(self.options)):
            raise ValueError("correctIndex out of range")
        if self.explanation is not None and not isinstance(self.explanation, str):
            raise ValueError("explanation must be string if provided")


@dataclass
class Quiz:
    ownerId: int
    title: str
    description: str = ""
    shuffleQuestions: bool = False
    shuffleOptions: bool = False
    perQuestionSeconds: Optional[int] = None
    totalSeconds: Optional[int] = None
    negativeMarking: float = 0.0
    questions: List[QuizQuestion] = field(default_factory=list)
    quizId: Optional[str] = None
    createdAt: datetime = field(default_factory=datetime.utcnow)

    def validate(self) -> None:
        if not isinstance(self.ownerId, int):
            raise ValueError("ownerId must be int")
        if not self.title or not isinstance(self.title, str):
            raise ValueError("title is required")
        if self.perQuestionSeconds is not None and (self.perQuestionSeconds <= 0 or self.perQuestionSeconds > 600):
            raise ValueError("perQuestionSeconds must be between 1 and 600")
        if self.totalSeconds is not None and (self.totalSeconds <= 0 or self.totalSeconds > 24 * 3600):
            raise ValueError("totalSeconds must be between 1 and 86400")
        if self.negativeMarking < 0 or self.negativeMarking > 1:
            raise ValueError("negativeMarking must be between 0 and 1")
        if not self.questions:
            raise ValueError("At least one question is required")
        for q in self.questions:
            q.validate()
        if self.quizId is None:
            self.quizId = _short_id_from_title(self.title)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quizId": self.quizId,
            "ownerId": self.ownerId,
            "title": self.title,
            "description": self.description,
            "shuffleQuestions": self.shuffleQuestions,
            "shuffleOptions": self.shuffleOptions,
            "perQuestionSeconds": self.perQuestionSeconds,
            "totalSeconds": self.totalSeconds,
            "negativeMarking": self.negativeMarking,
            "questions": [vars(q) for q in self.questions],
            "createdAt": self.createdAt,
        }


@dataclass
class QuizSession:
    sessionId: str
    quizId: str
    chatId: int
    isGroup: bool
    startedBy: int
    questionOrder: List[int]
    currentIndex: int = 0
    pollIdToQuestionIndex: Dict[str, int] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    answers: Dict[str, Dict[int, int]] = field(default_factory=dict)
    displayNames: Dict[str, str] = field(default_factory=dict)
    displayUsernames: Dict[str, str] = field(default_factory=dict)
    startedAt: datetime = field(default_factory=datetime.utcnow)
    endsAt: Optional[datetime] = None
    status: str = "pending"
    negativeMarking: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sessionId": self.sessionId,
            "quizId": self.quizId,
            "chatId": self.chatId,
            "isGroup": self.isGroup,
            "startedBy": self.startedBy,
            "questionOrder": self.questionOrder,
            "currentIndex": self.currentIndex,
            "pollIdToQuestionIndex": self.pollIdToQuestionIndex,
            "scores": self.scores,
            "answers": self.answers,
            "displayNames": self.displayNames,
            "displayUsernames": self.displayUsernames,
            "startedAt": self.startedAt,
            "endsAt": self.endsAt,
            "status": self.status,
            "negativeMarking": self.negativeMarking,
        }


