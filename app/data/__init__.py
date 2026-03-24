"""Shared application data catalogs."""

from app.data.curriculum import (
    EXERCISES,
    EXERCISE_MAP,
    EXPERIMENT_GROUPS,
    LEARNING_TRACKS,
    LANGUAGE_LABELS,
    QUIZ_BANK,
    QUIZ_BANK_BY_LANGUAGE,
    TOPIC_CONTENT,
    TOPICS,
    TOPIC_EXERCISES,
    get_quiz_questions,
    get_topic_content,
    get_track_exercises,
    get_track_topics,
    normalize_language,
)

__all__ = [
    "EXERCISES",
    "EXERCISE_MAP",
    "EXPERIMENT_GROUPS",
    "LEARNING_TRACKS",
    "LANGUAGE_LABELS",
    "QUIZ_BANK",
    "QUIZ_BANK_BY_LANGUAGE",
    "TOPIC_CONTENT",
    "TOPICS",
    "TOPIC_EXERCISES",
    "get_quiz_questions",
    "get_topic_content",
    "get_track_exercises",
    "get_track_topics",
    "normalize_language",
]
