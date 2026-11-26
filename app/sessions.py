"""In-memory conversation state per chat session."""
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings


@dataclass
class Session:
    employee_id: Optional[str] = None
    history: List[Tuple[str, str, str]] = field(default_factory=list)  # (user, assistant, intent)
    draft: Optional[Dict[str, Any]] = None  # unfinished leave application
    last_seen: float = field(default_factory=time.time)

    def remember(self, question: str, answer: str, intent: str) -> None:
        self.history.append((question, answer, intent))
        del self.history[: -max(settings.history_turns * 4, 1)]

    def policy_history(self) -> List[Tuple[str, str]]:
        """Recent policy Q&A turns, passed to the RAG service as follow-up context."""
        turns = [(q, a) for q, a, intent in self.history if intent == "policy_query"]
        return turns[-settings.history_turns:]


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def get(self, session_id: str, employee_id: str) -> Session:
        self._purge()
        session = self._sessions.setdefault(session_id, Session(employee_id=employee_id))
        if session.employee_id != employee_id:  # employee switched in the sidebar
            session.employee_id, session.history, session.draft = employee_id, [], None
        session.last_seen = time.time()
        return session

    def _purge(self) -> None:
        cutoff = time.time() - settings.session_ttl_minutes * 60
        for key in [k for k, s in self._sessions.items() if s.last_seen < cutoff]:
            del self._sessions[key]


sessions = SessionStore()
