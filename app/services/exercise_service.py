"""
Exercise Service
Handles code execution, test evaluation, and attempt processing
(Moved from app.py with zero modifications)
"""

import subprocess
import threading
import time as _time
from io import StringIO
from contextlib import redirect_stdout
from typing import Dict, List
from app.models import Attempt

# ─────────────────────────────────────────────
# Python Sandbox - Restricted Builtins
# ─────────────────────────────────────────────
SAFE_BUILTINS = {
    "print": print,
    "len":   len,
    "range": range,
    "int":   int,
    "float": float,
    "str":   str,
    "bool":  bool,
    "list":  list,
    "dict":  dict,
    "tuple": tuple,
    "set":   set,
    "abs":   abs,
    "round": round,
    "min":   min,
    "max":   max,
    "sum":   sum,
    "type":  type,
    "isinstance": isinstance,
    "enumerate":  enumerate,
    "zip":        zip,
    "sorted":     sorted,
    "reversed":   reversed,
    "True":  True,
    "False": False,
    "None":  None,
}


class ExerciseService:
    """
    Executes learner code and validates against test cases.
    All logic moved from app.py - zero behavior changes.
    """
    
    @staticmethod
    def run_code(code: str, language: str = "python", timeout: int = 5) -> Dict:
        """
        Execute learner code safely and return structured results.
        
        MOVED FROM: app.py/run_code() - ZERO MODIFICATIONS
        
        Returns:
            {
              "stdout": str,          # captured print output
              "error": str | None,    # error message if execution failed
              "error_type": str | None  # "syntax" | "runtime" | "timeout"
              "local_vars": dict      # variables defined in learner code
            }
        """
        result = {
            "stdout": "",
            "error": None,
            "error_type": None,
            "local_vars": {},
            "execution_time_ms": 0
        }
        _t_start = _time.monotonic()

        if language == "javascript":
            try:
                proc = subprocess.run(
                    ["node", "-e", code],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                result["stdout"] = (proc.stdout or "").strip()
                if proc.returncode != 0:
                    stderr = (proc.stderr or "").strip()
                    result["error"] = stderr.splitlines()[-1] if stderr else "JavaScript execution failed"
                    result["error_type"] = "syntax" if "SyntaxError" in stderr else "runtime"
            except subprocess.TimeoutExpired:
                result["error"] = "Execution timed out (possible infinite loop). Check your loop condition."
                result["error_type"] = "timeout"
            except FileNotFoundError:
                result["error"] = "Node.js runtime not found on server. Install Node.js to run JavaScript exercises."
                result["error_type"] = "runtime"
            result["execution_time_ms"] = round((_time.monotonic() - _t_start) * 1000, 1)
            return result

        # Python execution
        output_buffer = StringIO()
        local_ns = {}

        def _exec_python():
            try:
                safe_globals = {"__builtins__": SAFE_BUILTINS}
                with redirect_stdout(output_buffer):
                    exec(compile(code, "<learner>", "exec"), safe_globals, local_ns)
                result["stdout"] = output_buffer.getvalue().strip()
                result["local_vars"] = local_ns
            except SyntaxError as e:
                result["error"] = f"Syntax Error on line {e.lineno}: {e.msg}"
                result["error_type"] = "syntax"
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {e}"
                result["error_type"] = "runtime"

        thread = threading.Thread(target=_exec_python, daemon=True)
        thread.start()
        thread.join(timeout)

        result["execution_time_ms"] = round((_time.monotonic() - _t_start) * 1000, 1)

        if thread.is_alive():
            result["error"] = "Execution timed out (possible infinite loop). Check your loop condition."
            result["error_type"] = "timeout"

        return result

    @staticmethod
    def evaluate_test_cases(exercise: Dict, exec_result: Dict) -> Dict:
        """
        Compare execution result against exercise's test cases.
        
        MOVED FROM: app.py/evaluate_test_cases() - ZERO MODIFICATIONS
        
        Returns:
            {
              "passed": bool,
              "result": "pass" | "fail",
              "error_type": "syntax" | "runtime" | "logic" | "timeout" | None,
              "feedback": str,       # human-readable message
              "details": list        # per-test-case breakdown
            }
        """
        details = []

        # If code didn't even run, return immediately
        if exec_result["error"]:
            etype = exec_result["error_type"]
            return {
                "passed": False,
                "result": "fail",
                "error_type": etype,
                "feedback": exec_result["error"],
                "details": [{"test": "Execution", "passed": False, "message": exec_result["error"]}],
            }

        stdout = exec_result["stdout"]
        local_vars = exec_result["local_vars"]
        all_passed = True

        for i, tc in enumerate(exercise["test_cases"], 1):
            check = tc["check_type"]
            passed = False
            message = ""

            if check == "output":
                expected = tc["expected"].strip()
                actual = stdout.strip()
                passed  = actual == expected
                message = f"Expected output:\n  {expected}\nYour output:\n  {actual}" if not passed else "Correct output ✓"

            elif check == "output_contains":
                expected = tc["expected"].strip()
                passed  = expected in stdout
                message = f"Expected your output to contain:\n  {expected}\nYour output:\n  {stdout}" if not passed else f"Found '{expected}' in output ✓"

            elif check == "variable":
                var_name = tc["var"]
                expected_type = tc["expected_type"]
                if var_name not in local_vars:
                    message = f"Variable `{var_name}` was not found. Did you define it?"
                    passed  = False
                else:
                    actual_type = type(local_vars[var_name]).__name__
                    passed  = actual_type == expected_type
                    message = (
                        f"Variable `{var_name}` should be type `{expected_type}`, "
                        f"but got `{actual_type}`."
                    ) if not passed else f"Variable `{var_name}` is correct ✓"

            if not passed:
                all_passed = False

            details.append({"test": f"Test {i}", "passed": passed, "message": message})

        error_type = None if all_passed else "logic"

        return {
            "passed": all_passed,
            "result": "pass" if all_passed else "fail",
            "error_type": error_type,
            "feedback": "All test cases passed! Great work." if all_passed else "Some test cases failed. Review the details below.",
            "details": details,
        }
    
    @staticmethod
    def execute_and_evaluate(code: str, language: str, exercise: Dict, timeout: int = 5) -> Dict:
        """
        Complete exercise evaluation: Execute code and check against test cases
        
        Args:
            code: Learner's code submission
            language: "python" or "javascript"
            exercise: Exercise document from MongoDB with test_cases field
            timeout: Timeout in seconds (default 5)
        
        Returns:
            {
              "executed": bool,
              "compile_error": bool,
              "pass_fail": "pass" or "fail",
              "error_type": str,
              "feedback": str,
              "details": list,
              "execution_time_ms": float,
              "stdout": str,
            }
        """
        # Step 1: Execute the code
        exec_result = ExerciseService.run_code(code, language, timeout)
        
        # Step 2: Evaluate against test cases
        eval_result = ExerciseService.evaluate_test_cases(exercise, exec_result)
        
        return {
            "executed": exec_result["error"] is None,
            "compile_error": exec_result["error_type"] in ["syntax", "timeout"],
            "pass_fail": eval_result["result"],
            "error_type": eval_result["error_type"],
            "feedback": eval_result["feedback"],
            "details": eval_result["details"],
            "execution_time_ms": exec_result["execution_time_ms"],
            "stdout": exec_result["stdout"],
        }
