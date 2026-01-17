"""
Syntax Repair Guided Prompt

This module generates the comprehensive prompt for syntax repair phase.
It focuses on fixing YAML parsing errors and actionlint syntax errors.
"""

from prompts.shared import ALL_DEFENSE_RULES, ALL_YAML_GENERATION_RULES


def create_guided_syntax_repair_prompt(yaml_content: str, actionlint_errors: list) -> str:
    """
    Create a comprehensive guided prompt for syntax repair.
    
    Args:
        yaml_content: The YAML content to repair
        actionlint_errors: List of actionlint error messages
        
    Returns:
        Complete prompt string for LLM
    """
    
    # Role definition
    role_definition = """You are an expert GitHub Actions workflow repair assistant specialized in fixing syntax errors."""
    
    # Prohibitions
    prohibitions = """
STRICT PROHIBITIONS:
- NEVER add explanations or markdown formatting (e.g., ```yaml or comments)
- NEVER include multiple YAML documents in one output (no --- separators)
- Output ONLY valid YAML content that starts with workflow-level keys"""
    
    # Conservative Repair Principle (MOST IMPORTANT)
    conservative_principle = """

🚨 CONSERVATIVE REPAIR PRINCIPLE (CRITICAL - READ FIRST) 🚨

Your ONLY job is to fix the specific errors listed in the "ERRORS TO FIX" section below.
DO NOT make any other changes, improvements, optimizations, or refactoring.

MANDATORY RULES:
1. Fix ONLY the errors explicitly listed below
2. Keep EVERYTHING else EXACTLY as it appears in the original
3. Make the MINIMAL change required to fix each error
4. Preserve original structure, order, formatting, and naming
5. DO NOT add, remove, or reorder any working code
6. DO NOT "improve" or "optimize" working parts

CRITICAL EXAMPLES - Learn from these:

❌ WRONG: Error says "inputs at wrong location"
   → Delete the inputs section (simple but destroys functionality)

✅ CORRECT: Error says "inputs at wrong location"  
   → Move inputs to the correct location ONLY (preserves functionality)

❌ WRONG: Error says "missing runs-on key"
   → Reorganize entire job structure and add runs-on

✅ CORRECT: Error says "missing runs-on key"
   → Add ONLY "runs-on: ubuntu-latest" where needed

❌ WRONG: Error says "wrong indentation"
   → Reformat entire file and reorder keys

✅ CORRECT: Error says "wrong indentation"
   → Fix ONLY the indentation of the problematic line

VERIFICATION CHECKLIST before responding:
□ Did I fix ALL listed errors?
□ Did I make ONLY minimal changes to fix those errors?
□ Did I preserve ALL other code exactly as-is?
□ Did I avoid adding/removing/reordering working code?

Think: "What is the SMALLEST possible change to fix this specific error?"
"""
    
    # Special Syntax Rules (beyond shared rules)
    special_syntax_rules = """
SYNTAX REPAIR SPECIAL RULES:

Rule 6: Strict Indentation
- Use exactly 2 spaces for indentation (no tabs)
- Align list items correctly:
  jobs:
    build:
      steps:
        - name: Step 1
          uses: actions/checkout@v3

Rule 7: Structural Correctness
- Maintain proper YAML hierarchy (workflow → jobs → job → steps → step)
- Keep job-level keys (runs-on, needs, permissions) at job level
- Keep step-level keys (name, uses, run, with, env) at step level

Rule 8: Trigger and Filter Syntax
Rule 8A: Filter Branch Types
  - Use 'branches' (NOT 'branch')
  - Use 'tags' (NOT 'tag')
  - Use 'paths' (NOT 'path')

Rule 8B: String vs. List Context
  - Scalar context: branches: main
  - List context: branches: [main, develop]
  - NEVER: branches: 'main'  # Wrong in list context

Rule 8C: Paths Syntax
  - paths: ['src/**']        # Correct
  - paths-ignore: ['docs/**'] # Correct
  - NEVER: path-ignore        # Wrong key name

Rule 8D: Wildcard Escaping
  - In scalar: branch: 'feature/*'
  - In list: branches: ['feature/*']
  - NEVER unquoted wildcards"""
    
    # Assemble the complete prompt
    error_section = "\n".join([f"- {err}" for err in actionlint_errors])
    
    prompt = f"""{role_definition}

{conservative_principle}

{prohibitions}

{ALL_DEFENSE_RULES}

{ALL_YAML_GENERATION_RULES}

{special_syntax_rules}

ERRORS TO FIX:
{error_section}

WORKFLOW TO REPAIR:
{yaml_content}

OUTPUT: Provide ONLY the repaired YAML content (no explanations, no markdown).
"""
    
    return prompt
