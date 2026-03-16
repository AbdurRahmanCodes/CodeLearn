"""
Attempt Model
Represents a single code submission attempt
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict


@dataclass
class Attempt:
    """
    Attempt represents one code submission for an exercise
    
    Attributes:
        session_id: Which user session
        exercise_id: Which exercise (1-7)
        code: The submitted code
        language: "python" or "javascript"
        attempt_number: 1st, 2nd, 3rd attempt, etc.
        result: "pass" or "fail"
        error_type: Optional, for failures (syntaxError", "logicError", "testFailure")
        timestamp: When submitted
    """
    session_id: str
    exercise_id: int
    code: str
    language: str
    attempt_number: int
    result: str  # "pass" or "fail"
    error_type: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize defaults"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        
        # Validate result
        if self.result not in ["pass", "fail"]:
            raise ValueError("result must be 'pass' or 'fail'")
        
        # Validate language
        if self.language not in ["python", "javascript"]:
            raise ValueError("language must be 'python' or 'javascript'")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Attempt':
        """Create Attempt from MongoDB document"""
        return cls(
            session_id=data.get('session_id'),
            exercise_id=data.get('exercise_id'),
            code=data.get('code'),
            language=data.get('language'),
            attempt_number=data.get('attempt_number'),
            result=data.get('result'),
            error_type=data.get('error_type'),
            timestamp=data.get('timestamp'),
        )
