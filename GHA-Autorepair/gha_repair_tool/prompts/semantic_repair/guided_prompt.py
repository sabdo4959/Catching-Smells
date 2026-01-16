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

#### Smell 2: Outdated Action
- **Problem:** Security/Stability risks from old tags.
- **Solution:** Use Commit Hash (Secure) or latest major tag.
- **Example:** `uses: actions/checkout@v4`

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 4: Indentation** - Maintain 2-space indentation
- ✅ **Rule 3: Expression Syntax** - Keep existing `${{ }}` format intact

#### Smell 3: Deprecated Command
- **Problem:** `::set-output` fails in new runners.
- **Solution:** Use `$GITHUB_OUTPUT`.
- **Syntax:** `run: echo "{key}={value}" >> $GITHUB_OUTPUT`

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 4: Indentation** - Maintain 2-space indentation
- ✅ **Rule 3: Expression Syntax** - Use correct `${{ }}` syntax for variables
- ✅ **Rule 2: Shell Commands** - Ensure proper shell syntax in `run:` commands

#### Smell 4: Over-privileged Permissions (⚠️ PLACEMENT RULES - ENHANCED v3)
- **Problem:** Overly permissive token.
- **Solution:** Add `permissions` with specific rights.

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 4: Indentation** - Maintain 2-space indentation
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate `permissions` keys
- ✅ **Rule 9: Job Definition** - Keep existing job structure (runs-on + steps) intact

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

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 9: Job Definition Validation** - DO NOT create new jobs, only modify existing ones
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate job keys
- ✅ **Rule 4: Indentation** - Add timeout-minutes at correct indentation level (job level)
- ✅ **Defense Rule 2** - DO NOT add timeout if job uses reusable workflow (`uses: ./.github/...`)

**⚠️⚠️⚠️ ABSOLUTELY FORBIDDEN (Rule Violations):**
- ❌ Creating new job definitions at end of file → **Violates Rule 7 (duplicate keys) & Rule 9**
- ❌ Adding timeout to reusable workflow jobs → **Violates Defense Rule 2**
- ❌ Placing timeout outside job scope → **Violates Rule 4 (wrong indentation)**

- **🚨 CRITICAL EXCEPTION:** DO NOT add timeout if the job uses a Reusable Workflow (e.g., `uses: ./.github/...`). It causes syntax errors per Defense Rule 2.
```yaml
# ❌ WRONG:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR: Violates Defense Rule 2

# ✅ CORRECT - Add to existing job:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml  # No timeout (reusable workflow)
  
  regular:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # ✅ OK: Added INSIDE existing job, not creating new job
    steps:
      - run: npm build

# ❌ WRONG - Creating duplicate jobs:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build
  
  # Comment about timeouts
  build:  # ❌ FATAL ERROR: Duplicate job key! Violates Rule 1 & Rule 9
    timeout-minutes: 60
  test:  # ❌ FATAL ERROR: Duplicate job key!
    timeout-minutes: 60
```

#### Smell 6 & 7: Concurrency
- **Smell 6 (PR):** Add `concurrency` group with `cancel-in-progress: true`.
- **Smell 7 (Branch):** Add `concurrency` group for branches.

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 4: Indentation** - Add concurrency at workflow root level (same as `name:`, `on:`)
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate `concurrency` keys
- ✅ **Rule 3: Expression Syntax** - Use correct `${{ }}` syntax in group names

#### Smell 8: Missing Path Filter (⚠️ LIST SYNTAX & LOCATION REQUIRED - ENHANCED v3)
- **Problem:** Wasteful runs on doc changes.
- **Solution:** Add `paths-ignore` to `push` or `pull_request`.

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 4: Indentation** - Must be indented inside `on.push:` or `on.pull_request:`
- ✅ **Rule 8: List Format** - MUST use list format with hyphens (`- item`)
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate `paths-ignore` keys
- ✅ **Defense Rule 3** - MUST be inside trigger, NOT at job level

**⚠️⚠️⚠️ ABSOLUTELY FORBIDDEN (Rule Violations):**
- ❌ Adding `paths-ignore` at job level → **Violates Defense Rule 3 (wrong location)**
- ❌ Adding `paths-ignore` at workflow root → **Violates YAML structure**
- ❌ Using wrong format (not a list) → **Violates Rule 8**

- **🚨 SYNTAX:** MUST use list format with hyphens (`-`) per Defense Rule 3.
- **🚨 LOCATION:** MUST be INSIDE `on.push` or `on.pull_request`, NOT at job level or as sibling to `on`.
- **🚨 FORBIDDEN LOCATIONS (CAUSES ERRORS):**
  - ❌ NEVER at job level (inside `jobs.*.`)
  - ❌ NEVER inside steps
  - ❌ NEVER as sibling to `on:` (outside triggers)
  - ❌ NEVER at workflow root

**❌ WRONG - paths-ignore at job level:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build
    
    paths-ignore:  # ❌ ERROR: "unexpected key \\"paths-ignore\\" for \\"job\\" section"
      - '**.md'
```

**❌ WRONG - paths-ignore as sibling to on:**
```yaml
on:
  push:
    branches: [main]
paths-ignore:  # ❌ ERROR: Wrong location (outside push)
  - '**.md'
```

**❌ WRONG - paths-ignore at workflow root:**
```yaml
name: CI

paths-ignore:  # ❌ ERROR: Not a top-level key
  - '**.md'

on:
  push:
```

**✅ CORRECT - paths-ignore inside on.push:**
```yaml
on:
  push:
    branches: [main]
    paths-ignore:  # ✅ Correct: nested inside push
      - '**.md'    # List format with hyphen
      - 'docs/**'
  pull_request:
    branches: [main]
    paths-ignore:  # ✅ Also correct: nested inside pull_request
      - '**.md'
```

**VERIFICATION CHECKLIST:**
1. ✅ Is `paths-ignore` directly under `on.push:` or `on.pull_request:`?
2. ✅ Is it indented 2 spaces more than its parent trigger?
3. ✅ Are values in list format (`- item` or `[item1, item2]`)?
4. ❌ Is it NOT at job level, step level, or workflow root?

#### Smell 9: Run on Fork (Schedule) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Scheduled runs waste resources on forks.
- **Solution:** Add `if: github.repository_owner == 'owner'` to **THE FIRST EXISTING JOB** in the workflow.

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 9: Job Definition Validation** - DO NOT create new jobs without both `runs-on` AND `steps`
- ✅ **Rule 4: Indentation** - Maintain 2-space indentation consistently
- ✅ **Rule 3: Expression Syntax** - Use `${{ }}` for expressions (if needed)
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate job names

**🚨 CRITICAL RULES FOR THIS SMELL:**
  1. `on: schedule` DOES NOT support `if` per Defense Rule 1
  2. **NEVER CREATE A NEW JOB** - workflows already have jobs! (Rule 9 violation!)
  3. Add `if` condition to the **FIRST job** that already exists
  4. If workflow has `build`, `test`, `deploy` jobs → add `if` to `build`

**⚠️⚠️⚠️ ABSOLUTELY FORBIDDEN (Rule Violations):**
- ❌ Creating a new job named "scheduled-job" → **Violates Rule 7 (duplicate keys) & Rule 9**
- ❌ Creating any new job for this smell → **Violates Rule 9 (job must have runs-on + steps)**
- ❌ Adding empty jobs without steps → **Violates Rule 9 (job requires both runs-on AND steps)**
- ❌ Modifying existing job's runs-on or steps → **Unnecessary, only add if condition**

**✅ CORRECT - Modify EXISTING first job:**
```yaml
on:
  schedule:
    - cron: '0 0 * * *'

jobs:
  build:  # ✅ This job ALREADY EXISTS - just add if
    if: github.repository_owner == 'owner'  # ✅ ADD THIS LINE ONLY
    runs-on: ubuntu-latest  # ✅ Already exists - don't change
    steps:  # ✅ Already exists - don't change
      - run: npm build  # ✅ Already exists - don't change
  
  test:  # ✅ Other jobs unchanged
    runs-on: ubuntu-latest
    steps:
      - run: npm test
```

**❌ WRONG - DO NOT DO THIS:**
```yaml
on:
  schedule:
    - cron: '0 0 * * *'

jobs:
  build:  # Existing job - but you didn't add if here!
    runs-on: ubuntu-latest
    steps:
      - run: npm build
  
  scheduled-job:  # ❌ FATAL ERROR: You created a new job!
    if: github.repository_owner == 'owner'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Scheduled task"
```

**IMPLEMENTATION STEPS:**
1. Find the FIRST job in the `jobs:` section (e.g., `build:`, `test:`, etc.)
2. Add ONE line: `if: github.repository_owner == 'owner'` after the job name
3. DO NOT touch anything else (runs-on, steps remain unchanged)
4. DO NOT create new jobs (this would violate Rule 9!)

**BEFORE SUBMITTING - VERIFY RULES:**
- ✅ Rule 9: Did I add `if` to existing job WITHOUT creating new job?
- ✅ Rule 1: Are there NO duplicate job names?
- ✅ Rule 2: Is indentation correct (2 spaces)?
- ✅ Did I only modify ONE line (added `if` condition)?
4. DO NOT create new jobs

#### Smell 10: Run on Fork (Artifact) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Artifact uploads waste resources on forks.
- **Solution:** Add check before upload.

**🚨 MUST FOLLOW THESE YAML GENERATION RULES:**
- ✅ **Rule 7: Key Uniqueness** - DO NOT create duplicate `if` keys in same step
- ✅ **Rule 4: Indentation** - Add `if` at step level (same indentation as step name)
- ✅ **Rule 3: Expression Syntax** - Use correct `${{ }}` syntax for AND conditions
- ✅ **Rule 9: Job Definition** - Keep job structure intact, only modify step
- ✅ **Defense Rule 1** - NEVER add `if` to `on:` trigger section

**⚠️⚠️⚠️ CRITICAL: Handle Existing `if` Conditions:**
- **IF step already has `if` condition** → MERGE with AND operator `&&`
- **DO NOT create duplicate `if` keys** → Violates Rule 7!

- **🚨 CRITICAL LOCATION:** Add `if: github.repository_owner == ...` to the **STEP** using `upload-artifact`. NEVER in `on` per Defense Rule 1.

**✅ CORRECT - No existing if:**
```yaml
steps:
  - name: Upload artifact
    uses: actions/upload-artifact@v4
    if: github.repository_owner == 'owner'  # ✅ Add new if condition
    with:
      name: build
      path: dist/
```

**✅ CORRECT - Merge with existing if:**
```yaml
steps:
  - name: Upload installer for Mac
    if: runner.os == 'macOS' && github.repository_owner == 'owner'  # ✅ Merged with &&
    uses: actions/upload-artifact@v4
    with:
      name: installer-mac
      path: dist/
```

**❌ WRONG - Duplicate if keys:**
```yaml
steps:
  - name: Upload installer for Mac
    if: runner.os == 'macOS'  # Existing condition
    uses: actions/upload-artifact@v4
    if: github.repository_owner == 'owner'  # ❌ FATAL ERROR: Duplicate key! Violates Rule 7
    with:
      name: installer-mac
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
