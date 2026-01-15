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
