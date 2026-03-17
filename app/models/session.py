"""
Session Model
Represents a user's learning session state
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Session:
    """
    Session tracks the complete state of a user's learning journey
    
    Attributes:
        session_id: Unique identifier for this session
        user_mode: "static" (no explanations) or "interactive" (with feedback)
        experiment_arm: "A_control" or "B_adaptive"
        current_exercise_id: Which exercise user is on (1-7)
        quiz_scores_by_topic: {"variables": 80, "functions": 75, ...}
        recommendations_seen: [{"id": "rec_1", "clicked": True, "timestamp": datetime}, ...]
        created_at: When session started
        updated_at: Last update timestamp
    """
    session_id: str
    user_mode: Optional[str] = None  # "static" or "interactive"
    experiment_arm: Optional[str] = None  # "A_control" or "B_adaptive"
    current_exercise_id: Optional[int] = None
    quiz_scores_by_topic: Dict[str, int] = None
    recommendations_seen: List[Dict] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.quiz_scores_by_topic is None:
            self.quiz_scores_by_topic = {}
        if self.recommendations_seen is None:
            self.recommendations_seen = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        if isinstance(self.created_at, datetime):
            data['created_at'] = self.created_at
        if isinstance(self.updated_at, datetime):
            data['updated_at'] = self.updated_at
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        """Create Session from MongoDB document"""
        return cls(
            session_id=data.get('session_id'),
            user_mode=data.get('user_mode'),
            experiment_arm=data.get('experiment_arm'),
            current_exercise_id=data.get('current_exercise_id'),
            quiz_scores_by_topic=data.get('quiz_scores_by_topic', {}),
            recommendations_seen=data.get('recommendations_seen', []),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )
