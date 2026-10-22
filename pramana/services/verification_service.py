"""
Pramana Fix Confidence & Verification Service.
Performs safe static AST checks without executing user code.
"""

import ast
import re
from typing import Dict, Any, List

def check_balanced_delimiters(code: str) -> Dict[str, Any]:
    """Check matching brackets, parentheses, and braces."""
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    lines = code.split('\n')
    
    for line_idx, line in enumerate(lines, 1):
        # Ignore comments
        clean_line = re.sub(r'#.*|//.*', '', line)
        for col_idx, char in enumerate(clean_line, 1):
            if char in '({[':
                stack.append((char, line_idx, col_idx))
            elif char in ')}]':
                if not stack:
                    return {
                        'valid': False,
                        'message': f"Unmatched closing delimiter '{char}' at line {line_idx}, column {col_idx}",
                        'line': line_idx,
                        'col': col_idx
                    }
                top, top_line, top_col = stack.pop()
                if mapping[char] != top:
                    return {
                        'valid': False,
                        'message': f"Mismatched delimiter: opened '{top}' at line {top_line} but closed with '{char}' at line {line_idx}",
                        'line': line_idx,
                        'col': col_idx
                    }
                    
    if stack:
        char, line_idx, col_idx = stack[-1]
        return {
            'valid': False,
            'message': f"Unclosed delimiter '{char}' from line {line_idx}, column {col_idx}",
            'line': line_idx,
            'col': col_idx
        }
    return {'valid': True, 'message': 'All delimiters properly paired.'}


def verify_python_ast(code: str) -> Dict[str, Any]:
    """
    Parses code using Python's native AST module.
    NEVER executes code. Safe static inspection only.
    """
    if not code or not code.strip():
        return {
            'status': 'NOT VERIFIED',
            'verdict': 'Empty code snippet submitted.',
            'checks': [],
            'errors': ['No code provided for static analysis.'],
            'warnings': []
        }

    checks: List[Dict[str, str]] = []
    warnings: List[str] = []
    errors: List[str] = []

    # Check 1: Delimiter Matching
    delim_result = check_balanced_delimiters(code)
    if delim_result['valid']:
        checks.append({
            'name': 'Delimiter & Bracket Balance',
            'status': 'PASSED',
            'detail': 'Parentheses, brackets, and braces are correctly closed.'
        })
    else:
        checks.append({
            'name': 'Delimiter & Bracket Balance',
            'status': 'FAILED',
            'detail': delim_result['message']
        })

    # Check 2: Native AST Parse
    try:
        tree = ast.parse(code)
        checks.append({
            'name': 'Python AST Syntax Tree Generation',
            'status': 'PASSED',
            'detail': 'AST built successfully. Code contains 0 fatal syntax errors.'
        })

        # Check 3: Static code inspection on the parsed AST
        func_count = 0
        loop_count = 0
        branch_count = 0
        has_bare_except = False
        has_mutable_default = False
        has_literal_div_zero = False

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_count += 1
                # Check for mutable default argument e.g. def foo(x=[])
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        has_mutable_default = True
            elif isinstance(node, (ast.For, ast.While)):
                loop_count += 1
            elif isinstance(node, ast.If):
                branch_count += 1
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    has_bare_except = True
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    has_literal_div_zero = True

        checks.append({
            'name': 'Structural AST Inspection',
            'status': 'PASSED',
            'detail': f"Detected {func_count} function(s), {loop_count} loop(s), and {branch_count} branch(es)."
        })

        if has_mutable_default:
            warnings.append("Mutable default argument (list/dict/set) detected in function signature. May cause unexpected state sharing across calls.")
        if has_bare_except:
            warnings.append("Bare 'except:' clause detected. It is safer to catch specific exceptions like 'except Exception:'.")
        if has_literal_div_zero:
            warnings.append("Static division by zero detected in numeric constant expression.")

        status = 'CHECKS PASSED'
        verdict = 'Static AST validation passed. Syntax is structurally valid Python.'

    except SyntaxError as e:
        error_msg = f"SyntaxError at line {e.lineno}, column {e.offset or 0}: {e.msg}"
        errors.append(error_msg)
        checks.append({
            'name': 'Python AST Syntax Tree Generation',
            'status': 'FAILED',
            'detail': error_msg
        })
        status = 'CHECKS FAILED'
        verdict = f"Syntax check failed at line {e.lineno}: {e.msg}"

    except Exception as e:
        error_msg = f"Parser failure: {str(e)}"
        errors.append(error_msg)
        checks.append({
            'name': 'Python AST Syntax Tree Generation',
            'status': 'FAILED',
            'detail': error_msg
        })
        status = 'CHECKS FAILED'
        verdict = f"Static check encountered an error: {str(e)}"

    return {
        'status': status,
        'verdict': verdict,
        'checks': checks,
        'errors': errors,
        'warnings': warnings,
        'language': 'Python',
        'is_safe': True,
        'runtime_tested': False,
        'disclaimer': 'Static AST parsing validates syntactic correctness without execution. Program logic and runtime correctness are not guaranteed without automated test suite execution.'
    }


def verify_code(code: str, language: str = 'python') -> Dict[str, Any]:
    """General verification dispatcher."""
    lang = (language or 'python').lower().strip()
    
    if lang == 'python' or lang == 'py':
        return verify_python_ast(code)
    
    # Generic delimiter check for non-Python languages
    delim_result = check_balanced_delimiters(code)
    checks = [{
        'name': f'Delimiter & Bracket Matching ({language.title()})',
        'status': 'PASSED' if delim_result['valid'] else 'FAILED',
        'detail': delim_result['message']
    }]
    
    LANGUAGE_NAMES = {
        'python': 'Python',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'cpp': 'C++',
        'c': 'C',
        'java': 'Java',
        'go': 'Go',
        'rust': 'Rust'
    }
    display_lang = LANGUAGE_NAMES.get(lang, language.title())

    return {
        'status': 'NOT VERIFIED',
        'verdict': f'Partial structural check performed. Native compiler AST for {display_lang} is not hosted in this environment.',
        'checks': checks,
        'errors': [] if delim_result['valid'] else [delim_result['message']],
        'warnings': [f'Static analysis is natively implemented for Python. {display_lang} syntax requires local compiler/linter.'],
        'language': display_lang,
        'is_safe': True,
        'runtime_tested': False,
        'disclaimer': f'Code for {display_lang} has not been verified by an active compiler. Review cautiously before executing.'
    }
