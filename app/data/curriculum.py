"""Curriculum and experiment metadata shared across app modules."""

EXPERIMENT_GROUPS = ("A_control", "B_adaptive")

LANGUAGE_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
}

LEARNING_TRACKS = {
    "python": ["variables", "conditions", "loops", "functions"],
    "javascript": ["variables", "conditions", "loops", "functions"],
}

# Topic metadata by language. Each topic uses short videos for targeted remediation.
TOPIC_CONTENT = {
    "python": {
        "variables": {
            "title": "Python Variables and Assignment",
            "summary": "Store and update values using Python variables.",
            "video_url": "https://www.youtube.com/embed/kqtD5dpn9C8",
            "syntax_guide": "Use clear variable names and check quote usage in string literals.",
        },
        "conditions": {
            "title": "Python Conditional Logic",
            "summary": "Build if/elif/else branches for decision making.",
            "video_url": "https://www.youtube.com/embed/Zp5MuPOtsSY",
            "syntax_guide": "Check indentation and boolean expressions in if/elif/else statements.",
        },
        "loops": {
            "title": "Python Loops and Iteration",
            "summary": "Repeat logic using for and while loops.",
            "video_url": "https://www.youtube.com/embed/94UHCEmprCY",
            "syntax_guide": "Ensure loop counters change and stop conditions are reachable.",
        },
        "functions": {
            "title": "Python Functions",
            "summary": "Encapsulate reusable logic using def and return.",
            "video_url": "https://www.youtube.com/embed/NSbOtYzIQI0",
            "syntax_guide": "Define parameters clearly and ensure return values are used correctly.",
        },
    },
    "javascript": {
        "variables": {
            "title": "JavaScript Variables",
            "summary": "Use let/const to declare and manage values.",
            "video_url": "https://www.youtube.com/embed/W6NZfCO5SIk",
            "syntax_guide": "Prefer let/const and check semicolons or braces in declarations.",
        },
        "conditions": {
            "title": "JavaScript Conditions",
            "summary": "Use if/else and comparison operators to branch behavior.",
            "video_url": "https://www.youtube.com/embed/IsG4Xd6LlsM",
            "syntax_guide": "Verify comparison operators and code block braces.",
        },
        "loops": {
            "title": "JavaScript Loops",
            "summary": "Iterate with for, while, and for...of loops.",
            "video_url": "https://www.youtube.com/embed/s9wW2PpJsmQ",
            "syntax_guide": "Check loop increment/decrement and terminating conditions.",
        },
        "functions": {
            "title": "JavaScript Functions",
            "summary": "Create reusable function blocks with parameters.",
            "video_url": "https://www.youtube.com/embed/N8ap4k_1QEQ",
            "syntax_guide": "Confirm parameter names and return expressions.",
        },
    },
}

TOPICS = {
    "variables": {
        "title": "Variables and Assignment",
        "summary": "Store and update values using variables.",
        "video_url": "https://www.youtube.com/embed/kqtD5dpn9C8",
        "syntax_guide": "Use clear variable names and check quote usage in string literals.",
    },
    "arithmetic": {
        "title": "Arithmetic Operations",
        "summary": "Apply operators such as +, -, *, / and precedence rules.",
        "video_url": "https://www.youtube.com/embed/jZ5nY2x7uZw",
        "syntax_guide": "Check parentheses and operator order when results are unexpected.",
    },
    "strings": {
        "title": "String Operations",
        "summary": "Use built-in methods and length operations on text.",
        "video_url": "https://www.youtube.com/embed/R8rmfD9Y5-c",
        "syntax_guide": "Remember quotes and method call brackets such as .upper() or .length.",
    },
    "conditions": {
        "title": "Conditional Logic",
        "summary": "Build if/else decisions for branching behavior.",
        "video_url": "https://www.youtube.com/embed/f4KOjWS_KZs",
        "syntax_guide": "Check condition operators and block formatting in if/else statements.",
    },
    "loops": {
        "title": "Loops and Iteration",
        "summary": "Repeat actions with while and for loops.",
        "video_url": "https://www.youtube.com/embed/94UHCEmprCY",
        "syntax_guide": "Ensure loop counters change so the loop terminates.",
    },
    "functions": {
        "title": "Functions",
        "summary": "Encapsulate reusable logic with function definitions.",
        "video_url": "https://www.youtube.com/embed/NSbOtYzIQI0",
        "syntax_guide": "Define parameters clearly and ensure return values are used correctly.",
    },
}

QUIZ_BANK = {
    "variables": [
        {
            "id": "qv1",
            "question": "Which statement correctly stores the text hello in a variable x in Python?",
            "options": ["x = hello", "x = \"hello\"", "string x = hello", "x := text(hello)"],
            "answer": 1,
        },
        {
            "id": "qv2",
            "question": "What is the type of value 20 in Python?",
            "options": ["str", "float", "int", "bool"],
            "answer": 2,
        },
        {
            "id": "qv3",
            "question": "In JavaScript, which keyword declares a block-scoped variable?",
            "options": ["int", "var", "let", "define"],
            "answer": 2,
        },
    ],
    "conditions": [
        {
            "id": "qc1",
            "question": "Which operator checks equality in JavaScript?",
            "options": ["=", "==", "===", "!="],
            "answer": 2,
        },
        {
            "id": "qc2",
            "question": "What does this print in Python if x=4? if x>5: print('A') else: print('B')",
            "options": ["A", "B", "A then B", "Nothing"],
            "answer": 1,
        },
        {
            "id": "qc3",
            "question": "Which branch runs when a condition is false?",
            "options": ["if", "else", "def", "return"],
            "answer": 1,
        },
    ],
    "loops": [
        {
            "id": "ql1",
            "question": "What is the main risk with a while loop?",
            "options": ["Memory leak", "Infinite loop", "Syntax cannot compile", "No output"],
            "answer": 1,
        },
        {
            "id": "ql2",
            "question": "In JavaScript, which loop iterates over each element of an array?",
            "options": ["while", "for", "for...of", "switch"],
            "answer": 2,
        },
        {
            "id": "ql3",
            "question": "In Python, range(1, 4) produces:",
            "options": ["1,2,3", "1,2,3,4", "0,1,2,3", "Only 4"],
            "answer": 0,
        },
    ],
    "functions": [
        {
            "id": "qf1",
            "question": "What does a function return if there is no return statement in Python?",
            "options": ["0", "False", "None", "Empty string"],
            "answer": 2,
        },
        {
            "id": "qf2",
            "question": "Which line defines a JavaScript function add(a, b)?",
            "options": ["function add(a, b) { }", "def add(a,b):", "func add(a,b)", "add = function:"],
            "answer": 0,
        },
        {
            "id": "qf3",
            "question": "Why are functions useful in programming?",
            "options": ["They reduce reuse", "They avoid logic", "They improve reuse and readability", "They only print text"],
            "answer": 2,
        },
    ],
}

# Track-aligned quiz bank (language + topic). Legacy QUIZ_BANK is preserved for compatibility.
QUIZ_BANK_BY_LANGUAGE = {
    "python": {
        "variables": [
            {
                "id": "py_var_1",
                "question": "Which is a valid Python variable assignment?",
                "options": ["let x = 3", "x = 3", "var x := 3", "x == 3"],
                "answer": 1,
            },
            {
                "id": "py_var_2",
                "question": "Which type is produced by input() in Python?",
                "options": ["int", "bool", "str", "float"],
                "answer": 2,
            },
            {
                "id": "py_var_3",
                "question": "How do you create a string variable named name with value Alice?",
                "options": ["name = Alice", "name = 'Alice'", "str name = Alice", "name := text(Alice)"],
                "answer": 1,
            },
        ],
        "conditions": [
            {
                "id": "py_cond_1",
                "question": "Which keyword is used for an additional condition in Python?",
                "options": ["elseif", "elif", "else if", "when"],
                "answer": 1,
            },
            {
                "id": "py_cond_2",
                "question": "What does x == 5 check?",
                "options": ["Assignment", "Equality", "Type conversion", "Loop start"],
                "answer": 1,
            },
            {
                "id": "py_cond_3",
                "question": "Which block runs when all conditions fail?",
                "options": ["elif", "finally", "else", "except"],
                "answer": 2,
            },
        ],
        "loops": [
            {
                "id": "py_loop_1",
                "question": "Which loop can iterate directly over a list in Python?",
                "options": ["while", "for", "switch", "do while"],
                "answer": 1,
            },
            {
                "id": "py_loop_2",
                "question": "What is a common cause of infinite loops?",
                "options": ["Too many print statements", "No terminating condition update", "Using range", "Using integers"],
                "answer": 1,
            },
            {
                "id": "py_loop_3",
                "question": "range(2, 5) yields:",
                "options": ["2, 3, 4", "2, 3, 4, 5", "1, 2, 3, 4", "5 only"],
                "answer": 0,
            },
        ],
        "functions": [
            {
                "id": "py_fn_1",
                "question": "Which keyword defines a function in Python?",
                "options": ["function", "def", "fn", "lambda"],
                "answer": 1,
            },
            {
                "id": "py_fn_2",
                "question": "What does return do?",
                "options": ["Prints a value", "Stops execution and sends a value back", "Starts a loop", "Declares a variable"],
                "answer": 1,
            },
            {
                "id": "py_fn_3",
                "question": "If no return is used, Python returns:",
                "options": ["0", "False", "None", "''"],
                "answer": 2,
            },
        ],
    },
    "javascript": {
        "variables": [
            {
                "id": "js_var_1",
                "question": "Which declares a block-scoped variable?",
                "options": ["var", "let", "int", "define"],
                "answer": 1,
            },
            {
                "id": "js_var_2",
                "question": "Which is best for constants?",
                "options": ["var", "let", "const", "static"],
                "answer": 2,
            },
            {
                "id": "js_var_3",
                "question": "What is the assignment operator?",
                "options": ["==", "===", "=", "=>"],
                "answer": 2,
            },
        ],
        "conditions": [
            {
                "id": "js_cond_1",
                "question": "Which checks strict equality in JavaScript?",
                "options": ["==", "===", "=", "!="],
                "answer": 1,
            },
            {
                "id": "js_cond_2",
                "question": "Which block runs when condition is false?",
                "options": ["if", "else", "while", "for"],
                "answer": 1,
            },
            {
                "id": "js_cond_3",
                "question": "Which keyword starts conditional logic?",
                "options": ["when", "if", "switch", "try"],
                "answer": 1,
            },
        ],
        "loops": [
            {
                "id": "js_loop_1",
                "question": "Which loop iterates values in an array?",
                "options": ["for...of", "for...in", "switch", "if"],
                "answer": 0,
            },
            {
                "id": "js_loop_2",
                "question": "Infinite loops usually happen when:",
                "options": ["Arrays are empty", "Termination condition never changes", "You use let", "You use braces"],
                "answer": 1,
            },
            {
                "id": "js_loop_3",
                "question": "for (let i = 0; i < 3; i++) runs how many times?",
                "options": ["1", "2", "3", "4"],
                "answer": 2,
            },
        ],
        "functions": [
            {
                "id": "js_fn_1",
                "question": "Which defines a function named add?",
                "options": ["def add()", "function add() {}", "fn add()", "add := function"],
                "answer": 1,
            },
            {
                "id": "js_fn_2",
                "question": "What does return do in a function?",
                "options": ["Pauses code", "Sends value back to caller", "Prints output", "Declares variable"],
                "answer": 1,
            },
            {
                "id": "js_fn_3",
                "question": "Arrow function syntax uses:",
                "options": ["=>", "==>", "->", ":="],
                "answer": 0,
            },
        ],
    },
}

EXERCISES = [
    {
        "id": "ex01",
        "topic": "variables",
        "language": "python",
        "title": "Variables & Assignment",
        "description": "Create variable name (string) and age (20), then print each on a new line.",
        "example": "Output:\nAlice\n20",
        "starter_code": "# Write your code below\n",
        "explanation": "Variables store values you can reuse. Use quotes for strings and print() to output values.",
        "test_cases": [
            {"input": "", "check_type": "variable", "var": "name", "expected_type": "str"},
            {"input": "", "check_type": "variable", "var": "age", "expected_type": "int"},
        ],
    },
    {
        "id": "ex02",
        "topic": "conditions",
        "language": "python",
        "title": "If / Else in Python",
        "description": "Set score=72 and print Pass if score >= 50, otherwise print Fail.",
        "example": "Output:\nPass",
        "starter_code": "# Write your code below\n",
        "explanation": "Use if/else and indentation to control flow based on conditions.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "Pass"}],
    },
    {
        "id": "ex03",
        "topic": "loops",
        "language": "python",
        "title": "While Loop",
        "description": "Print numbers 1 to 5 using a while loop.",
        "example": "Output:\n1\n2\n3\n4\n5",
        "starter_code": "# Write your code below\n",
        "explanation": "Update loop counters to avoid infinite loops.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "1\n2\n3\n4\n5"}],
    },
    {
        "id": "ex04",
        "topic": "functions",
        "language": "python",
        "title": "Functions (Python)",
        "description": "Define celsius_to_fahrenheit(c), call with 100, print result.",
        "example": "Output:\n212.0",
        "starter_code": "# Write your code below\n",
        "explanation": "Functions encapsulate reusable logic and return computed values.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "212.0"}],
    },
    {
        "id": "ex05",
        "topic": "variables",
        "language": "javascript",
        "title": "Variables in JavaScript",
        "description": "Create variables name='Alice' and age=20, then print each using console.log.",
        "example": "Output:\nAlice\n20",
        "starter_code": "// Write your code below\n",
        "explanation": "Use let/const for declarations and console.log for output.",
        "test_cases": [
            {"input": "", "check_type": "output_contains", "expected": "Alice"},
            {"input": "", "check_type": "output_contains", "expected": "20"},
        ],
    },
    {
        "id": "ex06",
        "topic": "conditions",
        "language": "javascript",
        "title": "If / Else in JavaScript",
        "description": "Set score=72 and print Pass if score >= 50 else Fail.",
        "example": "Output:\nPass",
        "starter_code": "// Write your code below\n",
        "explanation": "Use if/else with braces and comparison operators.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "Pass"}],
    },
    {
        "id": "ex07",
        "topic": "loops",
        "language": "javascript",
        "title": "For Loop & Lists",
        "description": "Print each fruit from an array using for...of.",
        "example": "Output:\napple\nbanana\ncherry",
        "starter_code": "// Write your code below\n",
        "explanation": "Use for...of to iterate array values.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "apple\nbanana\ncherry"}],
    },
    {
        "id": "ex08",
        "topic": "functions",
        "language": "javascript",
        "title": "Functions (JavaScript)",
        "description": "Create function toFahrenheit(c) and print result for 100.",
        "example": "Output:\n212",
        "starter_code": "// Write your code below\n",
        "explanation": "Functions package reusable logic. Return computed values.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "212"}],
    },
]

EXERCISE_MAP = {ex["id"]: ex for ex in EXERCISES}
TOPIC_EXERCISES = {}
for ex in EXERCISES:
    TOPIC_EXERCISES.setdefault(ex["topic"], []).append(ex)


def normalize_language(language: str | None) -> str:
    """Return a supported language key with python as safe default."""
    lang = (language or "python").strip().lower()
    return lang if lang in LEARNING_TRACKS else "python"


def get_track_exercises(language: str | None) -> list[dict]:
    """Get exercises for a language track in pedagogical topic order."""
    lang = normalize_language(language)
    ordered_topics = LEARNING_TRACKS[lang]
    rows = [
        ex for ex in EXERCISES
        if ex.get("language") == lang and ex.get("topic") in ordered_topics
    ]
    rows.sort(key=lambda ex: ordered_topics.index(ex.get("topic")))
    return rows


def get_topic_content(language: str | None, topic: str) -> dict | None:
    """Get topic content for the selected language and topic."""
    lang = normalize_language(language)
    return TOPIC_CONTENT.get(lang, {}).get(topic)


def get_quiz_questions(language: str | None, topic: str) -> list[dict]:
    """Get topic-specific quiz questions for selected language track."""
    lang = normalize_language(language)
    return QUIZ_BANK_BY_LANGUAGE.get(lang, {}).get(topic, [])


def get_track_topics(language: str | None) -> dict:
    """Get ordered topic map for a language track."""
    lang = normalize_language(language)
    topic_order = LEARNING_TRACKS.get(lang, [])
    return {
        topic: TOPIC_CONTENT[lang][topic]
        for topic in topic_order
        if topic in TOPIC_CONTENT.get(lang, {})
    }
