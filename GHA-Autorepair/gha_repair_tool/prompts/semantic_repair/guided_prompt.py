"""
Semantic Repair Guided Prompt

This module generates the comprehensive prompt for semantic repair phase.
It focuses on fixing code smells (Smell 1-10) while maintaining syntax correctness.
"""

from prompts.shared import ALL_DEFENSE_RULES_WITH_RULE_0, ALL_YAML_GENERATION_RULES


def create_guided_semantic_repair_prompt(yaml_content: str, smells: list) -> str:
    """
    Create a comprehensive guided prompt for semantic repair.
    
    Args:
        yaml_content: The YAML content with syntax errors already fixed
        smells: List of detected code smells
        
    Returns:
        Complete prompt string for LLM
    """
    
    # Role and instructions
    role_and_instructions = """### ROLE ###
You are a "Professional DevOps Engineer" who fixes ONLY the 'Specific Code Smell List' in GitHub Actions workflows according to best practices.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Semantic Smell List' listed below according to GitHub best practices.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER fix smells or other code quality issues not listed.
- NEVER change code not directly related to smell fixes.
- Fix smells while maintaining the core functionality, behavior sequence, if conditions, and other structural/logical flow of the existing workflow."""
    
    # Smell-specific repair guidelines
    smell_fix_instructions = """
### 🔧 CODE SMELL REPAIR GUIDELINES ###

#### Smell 1: Outdated Action
- **Problem:** Security/Stability risks from old tags.
- **Solution:** Use Commit Hash (Secure) or latest major tag.
- **Example:** `uses: actions/checkout@v4`

#### Smell 2: Deprecated Command
- **Problem:** `::set-output` fails in new runners.
- **Solution:** Use `$GITHUB_OUTPUT`.
- **Syntax:** `run: echo "{key}={value}" >> $GITHUB_OUTPUT`

#### Smell 3: Over-privileged Permissions (⚠️ PLACEMENT RULES - ENHANCED v3)
- **Problem:** Overly permissive token.
- **Solution:** Add `permissions` with specific rights.
- **🚨 VALID LOCATIONS (ONLY 2 OPTIONS):**
  1. **Workflow-level**: At root, alongside `name:`, `on:`, `jobs:`
  2. **Job-level**: Inside a job, alongside `runs-on:`, `steps:`
- **🚨 FORBIDDEN LOCATION:**
  - ❌ NEVER at step-level (causes "unexpected key \\"permissions\\" for \\"step\\" section" error)

**❌ WRONG - permissions at step level:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Push code
        permissions:         # ❌ ERROR: Not allowed in steps
          contents: write
        run: git push
```

**✅ CORRECT - permissions at job level:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:         # ✅ Correct: job-level
      contents: write
    steps:
      - name: Push code
        run: git push
```

**✅ ALSO CORRECT - permissions at workflow level:**
```yaml
name: Deploy
on: [push]

permissions:             # ✅ Correct: workflow-level (root)
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: git push
```

**DECISION LOGIC:**
- **For one specific job** needing permissions: Add at **job-level**
- **For entire workflow** needing permissions: Add at **workflow-level** (root)
- **NEVER** at step-level (steps don't support `permissions` key)

#### Smell 5: Missing Job Timeout (⚠️ EXCEPTION FOR REUSABLE WORKFLOWS)
- **Problem:** Jobs running indefinitely.
- **Solution:** Add `timeout-minutes: 60` to jobs.
- **🚨 CRITICAL EXCEPTION:** DO NOT add timeout if the job uses a Reusable Workflow (e.g., `uses: ./.github/...`). It causes syntax errors per Defense Rule 2.
```yaml
# ❌ WRONG:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR

# ✅ CORRECT:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml  # No timeout
  
  regular:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # OK
```

#### Smell 6 & 7: Concurrency
- **Smell 6 (PR):** Add `concurrency` group with `cancel-in-progress: true`.
- **Smell 7 (Branch):** Add `concurrency` group for branches.

#### Smell 8: Missing Path Filter
- **Problem:** Wasteful CI runs triggered by documentation or non-code changes.
- **Solution:** Add `paths-ignore` filter to skip unnecessary builds.
- **🚨 CRITICAL:** Follow **Rule 8E (Filter Nesting)** and **Rule 8B (Structure Types)** from YAML Generation Rules.

**Key Requirements:**
1. **Location:** `paths-ignore` MUST be nested INSIDE `on.push` or `on.pull_request` (NOT at job level, NOT as sibling to `on`)
2. **Format:** MUST use list syntax with wildcards quoted: `['**.md', 'docs/**']`
3. **Common patterns:** `'**.md'` (markdown files), `'docs/**'` (docs folder), `'*.txt'` (text files)

**✅ CORRECT Example:**
```yaml
on:
  push:
    branches: [main]
    paths-ignore:       # ✅ Inside push trigger
      - '**.md'
      - 'docs/**'
  pull_request:
    paths-ignore:       # ✅ Inside pull_request trigger  
      - '**.md'
```

**❌ COMMON ERRORS:**
```yaml
# Error 1: At job level
jobs:
  build:
    paths-ignore: ['**.md']  # ❌ "unexpected key paths-ignore for job section"

# Error 2: As sibling to on
on:
  push:
paths-ignore: ['**.md']      # ❌ Wrong nesting level

# Error 3: At workflow root
paths-ignore: ['**.md']      # ❌ Not a top-level key
```

**📖 See:** YAML Generation Rules - Rule 8E for detailed filter nesting rules.

#### Smell 9: Run on Fork (Schedule) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Scheduled runs waste resources on forks.
- **Solution:** Add repo owner check.
- **🚨 CRITICAL LOCATION:** `on: schedule` DOES NOT support `if` per Defense Rule 1. You MUST add `if: github.repository_owner == ...` at the **JOB level**.
```yaml
# ✅ CORRECT:
on:
  schedule:
    - cron: '0 0 * * *'  # No if here

jobs:
  scheduled-job:
    if: github.repository_owner == 'owner'  # Check at job level
    runs-on: ubuntu-latest
```

#### Smell 10: Run on Fork (Artifact) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Artifact uploads waste resources on forks.
- **Solution:** Add check before upload.
- **🚨 CRITICAL LOCATION:** Add `if: github.repository_owner == ...` to the **STEP** using `upload-artifact`. NEVER in `on` per Defense Rule 1.
```yaml
# ✅ CORRECT:
steps:
  - name: Upload artifact
    uses: actions/upload-artifact@v4
    if: github.repository_owner == 'owner'  # Check at step level
    with:
      name: build
      path: dist/
```
"""
    
    # Assemble the complete prompt
    smell_section = ""
    for i, smell in enumerate(smells, 1):
        smell_section += f"{i}. **{smell.get('type', 'Unknown')}**: {smell.get('description', 'No description')}\n"
        if smell.get('location'):
            smell_section += f"   Location: {smell['location']}\n"
        if smell.get('suggestion'):
            smell_section += f"   Suggestion: {smell['suggestion']}\n"
    
    prompt = f"""{role_and_instructions}

{ALL_DEFENSE_RULES_WITH_RULE_0}

{smell_fix_instructions}

{ALL_YAML_GENERATION_RULES}

**Current YAML (syntax errors already fixed):**
```yaml
{yaml_content}
```

**Code Smells to Fix:**
{smell_section}

Provide an improved YAML that fixes each smell according to GitHub Actions best practices:

**Response Format:**
```yaml
# Fixed workflow
```
"""
    
    return prompt
