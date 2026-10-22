"""
Pramana Game Mode Challenge Repository.
Contains curated challenges for:
- Game A: Fix the Bug
- Game B: Find the Error
- Game C: Explain the Code
Across Beginner, Intermediate, and Advanced difficulties.
"""

from typing import Dict, Any, List

GAMES_CONFIG = {
    "game_a": {
        "id": "game_a",
        "title": "Fix The Bug",
        "tagline": "Spot the flaw and apply the minimal correct code fix.",
        "icon": "bi-wrench-adjustable",
        "badge_color": "primary"
    },
    "game_b": {
        "id": "game_b",
        "title": "Find The Error",
        "tagline": "Scan the code and pinpoint the exact line causing the crash.",
        "icon": "bi-crosshair",
        "badge_color": "warning"
    },
    "game_c": {
        "id": "game_c",
        "title": "Explain The Code",
        "tagline": "Trace execution step-by-step and predict output or purpose.",
        "icon": "bi-lightbulb",
        "badge_color": "info"
    }
}

CHALLENGES: List[Dict[str, Any]] = [
    # ==========================================
    # GAME A: FIX THE BUG
    # ==========================================
    {
        "id": "ga-1",
        "game_type": "game_a",
        "difficulty": "Beginner",
        "title": "Off-by-One in Array Accumulation",
        "language": "python",
        "xp_reward": 50,
        "code": """def calculate_total(prices):\n    total = 0\n    for i in range(len(prices) + 1):\n        total += prices[i]\n    return total\n\nprint(calculate_total([10, 20, 30]))""",
        "prompt": "This function throws an IndexError when executed. How should the range loop be corrected?",
        "options": [
            "for i in range(len(prices)):",
            "for i in range(1, len(prices) + 1):",
            "for i in range(len(prices) - 1):",
            "for i in len(prices):"
        ],
        "correct_answer": "for i in range(len(prices)):",
        "solution_code": """def calculate_total(prices):\n    total = 0\n    for i in range(len(prices)):\n        total += prices[i]\n    return total\n\nprint(calculate_total([10, 20, 30]))""",
        "explanation": "In zero-indexed languages like Python, an array of length N has valid indices 0 to N-1. `range(len(prices) + 1)` attempts to access index N, triggering an IndexError. Replacing it with `range(len(prices))` or simply iterating with `for p in prices:` resolves the bug.",
        "root_cause": "Loop upper bound exceeds valid list index bounds."
    },
    {
        "id": "ga-2",
        "game_type": "game_a",
        "difficulty": "Intermediate",
        "title": "The Mutable Default Argument Trap",
        "language": "python",
        "xp_reward": 75,
        "code": """def append_task(task, tasks=[]):\n    tasks.append(task)\n    return tasks\n\nuser1 = append_task("Email Bob")\nuser2 = append_task("Write Report")\nprint(user2) # Unexpectedly prints ['Email Bob', 'Write Report']""",
        "prompt": "user2 receives tasks from user1 because default arguments are evaluated once at function definition time. What is the standard Python idiom to fix this?",
        "options": [
            "def append_task(task, tasks=None): if tasks is None: tasks = []",
            "def append_task(task, tasks=list()): tasks.clear()",
            "def append_task(task, tasks=[]): tasks = tasks.copy()",
            "def append_task(task, tasks=()): tasks.append(task)"
        ],
        "correct_answer": "def append_task(task, tasks=None): if tasks is None: tasks = []",
        "solution_code": """def append_task(task, tasks=None):\n    if tasks is None:\n        tasks = []\n    tasks.append(task)\n    return tasks\n\nuser1 = append_task("Email Bob")\nuser2 = append_task("Write Report")\nprint(user2) # Output: ['Write Report']""",
        "explanation": "In Python, default parameter values are created when the function definition is executed, NOT each time the function is called. Using `tasks=None` as the default and instantiating a fresh `[]` inside the function ensures independent list instances per invocation.",
        "root_cause": "Mutable object (list) shared across function invocations as default parameter."
    },
    {
        "id": "ga-3",
        "game_type": "game_a",
        "difficulty": "Advanced",
        "title": "Late Binding Closures in Loops",
        "language": "python",
        "xp_reward": 100,
        "code": """def create_multipliers():\n    multipliers = []\n    for i in range(3):\n        multipliers.append(lambda x: x * i)\n    return multipliers\n\nfuncs = create_multipliers()\nprint([f(2) for f in funcs]) # Prints [4, 4, 4] instead of [0, 2, 4]""",
        "prompt": "All lambdas evaluate with i=2 because Python closures bind variables by reference, not value. How do you bind i at definition time?",
        "options": [
            "multipliers.append(lambda x, i=i: x * i)",
            "multipliers.append(lambda x: x * int(i))",
            "multipliers.append(lambda x: x * copy(i))",
            "multipliers.append(lambda x: x * i.value)"
        ],
        "correct_answer": "multipliers.append(lambda x, i=i: x * i)",
        "solution_code": """def create_multipliers():\n    multipliers = []\n    for i in range(3):\n        multipliers.append(lambda x, i=i: x * i)\n    return multipliers\n\nfuncs = create_multipliers()\nprint([f(2) for f in funcs]) # Prints [0, 2, 4]""",
        "explanation": "By providing `i=i` as a default parameter in the lambda definition, the current value of `i` in the loop iteration is captured and locked into the lambda's local default argument environment, preventing late binding lookup from outer scope.",
        "root_cause": "Closure references loop variable dynamically looked up at evaluation time."
    },

    # ==========================================
    # GAME B: FIND THE ERROR
    # ==========================================
    {
        "id": "gb-1",
        "game_type": "game_b",
        "difficulty": "Beginner",
        "title": "String and Integer Concatenation",
        "language": "python",
        "xp_reward": 40,
        "code": """# Line 1: Calculate age message\nname = "Alice"           # Line 2\nage = 20                  # Line 3\nmsg = name + " is " + age # Line 4\nprint(msg)                # Line 5""",
        "prompt": "Which line causes a TypeError when this script executes?",
        "options": [
            "Line 2",
            "Line 3",
            "Line 4",
            "Line 5"
        ],
        "correct_answer": "Line 4",
        "solution_code": """name = "Alice"\nage = 20\nmsg = name + " is " + str(age) # Fixed with str(age) or f-string\nprint(msg)""",
        "explanation": "Line 4 attempts to concatenate string variables with an integer (`age = 20`) using the `+` operator. Python is strongly typed and does not perform implicit string type coercion. You must convert `age` with `str(age)` or use an f-string: `f'{name} is {age}'`.",
        "root_cause": "TypeError: can only concatenate str (not 'int') to str on Line 4."
    },
    {
        "id": "gb-2",
        "game_type": "game_b",
        "difficulty": "Intermediate",
        "title": "Dictionary Key Access Error",
        "language": "python",
        "xp_reward": 60,
        "code": """config = {"host": "localhost", "port": 8080} # Line 1\ndb_user = config["user"]                      # Line 2\nprint(f"Connecting as {db_user}")             # Line 3""",
        "prompt": "Which line crashes with a KeyError?",
        "options": [
            "Line 1",
            "Line 2",
            "Line 3",
            "No error occurs"
        ],
        "correct_answer": "Line 2",
        "solution_code": """config = {"host": "localhost", "port": 8080}\ndb_user = config.get("user", "guest") # Safe access\nprint(f"Connecting as {db_user}")""",
        "explanation": "Line 2 attempts direct key subscripting `config['user']` on a dictionary where the key `'user'` does not exist. This immediately raises a `KeyError`. Using `config.get('user', 'default')` prevents the crash by returning a safe fallback.",
        "root_cause": "KeyError due to unhandled non-existent dictionary key access."
    },
    {
        "id": "gb-3",
        "game_type": "game_b",
        "difficulty": "Advanced",
        "title": "Modifying List While Iterating",
        "language": "python",
        "xp_reward": 85,
        "code": """numbers = [1, 2, 3, 4, 5, 6]      # Line 1\nfor num in numbers:               # Line 2\n    if num % 2 == 0:              # Line 3\n        numbers.remove(num)       # Line 4\nprint(numbers)                    # Line 5""",
        "prompt": "Line 4 alters the list size during iteration, silently skipping elements (prints [1, 3, 5, 6] or unexpected results). Which line causes the behavioral failure?",
        "options": [
            "Line 2",
            "Line 3",
            "Line 4",
            "Line 5"
        ],
        "correct_answer": "Line 4",
        "solution_code": """numbers = [1, 2, 3, 4, 5, 6]\n# Fix: Iterate over a slice copy or use list comprehension\nnumbers = [num for num in numbers if num % 2 != 0]\nprint(numbers) # [1, 3, 5]""",
        "explanation": "Modifying a container (via `numbers.remove(num)`) while iterating over it in a `for` loop disrupts the internal iterator index counter. When an item is removed, subsequent elements shift left, causing the iterator to skip the immediate next element.",
        "root_cause": "Mutating collection length during live forward iteration."
    },

    # ==========================================
    # GAME C: EXPLAIN THE CODE
    # ==========================================
    {
        "id": "gc-1",
        "game_type": "game_c",
        "difficulty": "Beginner",
        "title": "List Slicing Step Direction",
        "language": "python",
        "xp_reward": 35,
        "code": """word = "Pramana"\nreversed_word = word[::-1]\nprint(reversed_word)""",
        "prompt": "What does the slice expression `word[::-1]` do, and what will be printed?",
        "options": [
            "Prints 'anamarP' (reverses the entire string using negative step -1)",
            "Prints 'Pramana' (makes an exact duplicate copy)",
            "Prints 'P' (extracts only the first character)",
            "Throws a ValueError because negative step is disallowed on strings"
        ],
        "correct_answer": "Prints 'anamarP' (reverses the entire string using negative step -1)",
        "solution_code": """word = "Pramana"\nreversed_word = word[::-1]\nprint(reversed_word) # Output: anamarP""",
        "explanation": "Python slice syntax follows `[start:stop:step]`. Omitting `start` and `stop` selects the entire sequence, and setting `step = -1` traverses the sequence backwards from the last element to the first, producing 'anamarP'.",
        "root_cause": "Sequence slicing with negative step increments."
    },
    {
        "id": "gc-2",
        "game_type": "game_c",
        "difficulty": "Intermediate",
        "title": "Boolean Short-Circuit Evaluation",
        "language": "python",
        "xp_reward": 55,
        "code": """def ping():\n    print("Ping!")\n    return False\n\ndef pong():\n    print("Pong!")\n    return True\n\nresult = ping() and pong()\nprint("Result:", result)""",
        "prompt": "What does this program print to standard output?",
        "options": [
            "Ping!\nResult: False",
            "Ping!\nPong!\nResult: False",
            "Pong!\nResult: True",
            "Result: False"
        ],
        "correct_answer": "Ping!\nResult: False",
        "solution_code": """result = ping() and pong()\n# Ping! is evaluated. Since it returns False, the 'and' expression\n# short-circuits and never executes pong().""",
        "explanation": "Python logical operators (`and`, `or`) use short-circuit evaluation. In expression `A and B`, if `A` evaluates to false, the entire expression cannot possibly be true, so `B` (`pong()`) is never called or executed. Hence only 'Ping!' is printed.",
        "root_cause": "Short-circuit boolean logic skips right-hand expression when left-hand determines result."
    },
    {
        "id": "gc-3",
        "game_type": "game_c",
        "difficulty": "Advanced",
        "title": "Generator vs List Comprehension Memory",
        "language": "python",
        "xp_reward": 80,
        "code": """import sys\ngen = (x * 2 for x in range(1000000))\nlst = [x * 2 for x in range(1000000)]\nprint(type(gen).__name__, sys.getsizeof(gen) < sys.getsizeof(lst))""",
        "prompt": "What is the output and core architectural difference between `(x for x in ...)` and `[x for x in ...]`?",
        "options": [
            "generator True (generators evaluate lazily on-demand consuming constant O(1) memory)",
            "tuple False (parentheses create immutable tuples which take more memory)",
            "generator False (generators pre-allocate memory buffers)",
            "list True (both create lists with identical memory footprints)"
        ],
        "correct_answer": "generator True (generators evaluate lazily on-demand consuming constant O(1) memory)",
        "solution_code": """# Output: generator True\n# Generator expressions do not build the full million-element array in RAM;\n# they yield values one at a time on demand.""",
        "explanation": "Parentheses `(...)` create a generator object that evaluates lazily using the iterator protocol, maintaining fixed tiny memory overhead (~100-200 bytes) regardless of range size. Square brackets `[...]` immediately allocate and populate a full million-item list in memory (~8MB+).",
        "root_cause": "Lazy iterator evaluation vs eager memory allocation."
    }
]


def get_all_challenges() -> List[Dict[str, Any]]:
    """Returns all available challenges sanitized for public listing (hiding raw answer keys)."""
    sanitized = []
    for c in CHALLENGES:
        item = {
            "id": c["id"],
            "game_type": c["game_type"],
            "difficulty": c["difficulty"],
            "title": c["title"],
            "language": c["language"],
            "xp_reward": c["xp_reward"],
            "code": c["code"],
            "prompt": c["prompt"],
            "options": c["options"]
        }
        sanitized.append(item)
    return sanitized


def validate_game_answer(challenge_id: str, user_answer: str) -> Dict[str, Any]:
    """
    Validates a submitted answer against the challenge solution.
    Provides detailed explanation, correction, and awarded XP.
    """
    challenge = next((c for c in CHALLENGES if c["id"] == challenge_id), None)
    if not challenge:
        return {
            "success": False,
            "error": "Challenge not found."
        }

    clean_user = user_answer.strip().lower()
    clean_correct = challenge["correct_answer"].strip().lower()

    # Exact or substring match (for multiple choice or normalized line numbers)
    is_correct = (clean_user == clean_correct) or (clean_correct in clean_user) or (clean_user in clean_correct)

    # Line number shorthand e.g. "4" vs "Line 4"
    if not is_correct and "line" in clean_correct:
        num = ''.join(filter(str.isdigit, clean_correct))
        user_num = ''.join(filter(str.isdigit, clean_user))
        if num and user_num and num == user_num:
            is_correct = True

    return {
        "success": True,
        "is_correct": is_correct,
        "xp_awarded": challenge["xp_reward"] if is_correct else 0,
        "correct_answer": challenge["correct_answer"],
        "solution_code": challenge["solution_code"],
        "explanation": challenge["explanation"],
        "root_cause": challenge.get("root_cause", ""),
        "difficulty": challenge["difficulty"]
    }
