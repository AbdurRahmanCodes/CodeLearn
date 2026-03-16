"""
QuizAttempt Model
Represents a quiz submission
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict


@dataclass
class QuizAttempt:
    """
    QuizAttempt represents one quiz submission
    
    Attributes:
        session_id: Which user session
        topic: Which topic ("variables", "loops", "functions", etc.)
        score: Points earned
        total: Total possible points
        timestamp: When submitted
    """
    session_id: str
    topic: str
    score: int
    total: int
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize defaults and validate"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        
        if self.score < 0 or self.total <= 0:
            raise ValueError("score must be >= 0, total must be > 0")
        
        if self.score > self.total:
            raise ValueError("score cannot exceed total")
    
    @property
    def score_percentage(self) -> float:
        """Calculate percentage score"""
        return (self.score / self.total * 100) if self.total > 0 else 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        data['score_percentage'] = self.score_percentage
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QuizAttempt':
        """Create QuizAttempt from MongoDB document"""
        return cls(
            session_id=data.get('session_id'),
            topic=data.get('topic'),
            score=data.get('score'),
            total=data.get('total'),
            timestamp=data.get('timestamp'),
        )
