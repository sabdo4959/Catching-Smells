"""
Defense Rules - Anti-Regression Guardrails

These rules prevent the LLM from creating new errors while fixing existing ones.
Shared between Syntax and Semantic repair phases.

Version History:
- v1.0: Initial rules 0-2 (NO duplicate keys, NO if in triggers, NO timeout for reusable)
- v2.0: Added rules 3-4 (Strict list syntax, Separate uses/run)
- v3.0: Enhanced examples and clarifications

References:
- GitHub Actions Schema: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- actionlint Rules: https://github.com/rhysd/actionlint
"""

# ==============================================================================
# Defense Rule 0: NO Duplicate Keys (CRITICAL FOR SEMANTIC REPAIR)
# ==============================================================================

DEFENSE_RULE_0_NO_DUPLICATE_KEYS = """
#### Defense Rule 0: 👯 NO Duplicate Keys (CRITICAL FOR SEMANTIC REPAIR)
- **CONTEXT:** When fixing smells (e.g., Smell 9, Smell 6, Smell 4), you will ADD new code.
- **FATAL ERROR:** Creating a second `jobs:`, `on:`, `env:`, `permissions:`, or `concurrency:` section causes "key is duplicated" error.
- **STRICT INSTRUCTION:**
  1. **LOOK FIRST:** Does `jobs:` already exist in the file? (It almost ALWAYS does!)
  2. **MERGE:** Write your new job/env/permission **INSIDE** the existing block.
  3. **NEVER:** Write `jobs:` or `on:` again at the bottom of the file.

**EXAMPLES:**

**❌ WRONG - Creating duplicate jobs:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest  # Existing job

# ... (many lines later) ...

jobs:  # ❌ DUPLICATE KEY ERROR!
  scheduled-job:  # Smell 9 fix - WRONG APPROACH
    if: github.repository_owner == 'owner'
    runs-on: ubuntu-latest
```

**✅ CORRECT - Merge into existing jobs:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest  # Existing job
  
  scheduled-job:  # ✅ Added as sibling job (same indentation as 'build')
    if: github.repository_owner == 'owner'
    runs-on: ubuntu-latest
```

**❌ WRONG - Creating duplicate permissions:**
```yaml
permissions:
  contents: read  # Existing

# ... later ...
permissions:  # ❌ DUPLICATE KEY ERROR!
  issues: write  # Smell 4 fix - WRONG APPROACH
```

**✅ CORRECT - Merge into existing permissions:**
```yaml
permissions:
  contents: read  # Existing
  issues: write   # ✅ Added to same permissions block
```
"""

# ==============================================================================
# Defense Rule 1: NO `if` in `on` / `triggers` (FATAL ERROR - HIGHEST PRIORITY)
# ==============================================================================

DEFENSE_RULE_1_NO_IF_IN_TRIGGERS = """
#### Defense Rule 1: 🚨 NO `if` in `on` / `triggers` (FATAL ERROR - HIGHEST PRIORITY)
- **FATAL ERROR:** `unexpected key "if" for "push" section` or `"pull_request" section`
- **Root Cause:** `on:` section defines WHEN to trigger (static config). NO runtime conditions allowed.
- **STRICTLY FORBIDDEN:**
  - ❌ ANY `if:` key inside `on:` section
  - ❌ `${{ github.* }}` expressions inside `on:`
  - ❌ Conditional logic in triggers (push, pull_request, schedule, workflow_dispatch, etc.)

**CRITICAL FIX PATTERN (Most Common Error):**
```yaml
# ❌ WRONG (CAUSES FATAL ERROR):
on:
  push:
    branches: [main]
    if: github.event.after == 'xxx'  # ❌ ERROR

# ✅ CORRECT (Move to Job Level):
on:
  push:
    branches: [main]  # ✅ Clean trigger

jobs:
  build:
    if: github.event.after == 'xxx'  # ✅ Condition at job level
    runs-on: ubuntu-latest
```

**Multi-Trigger Pattern (Common Failure Case):**
```yaml
# ❌ WRONG:
on:
  push:
    if: github.repository == 'owner/repo'  # ❌ ERROR
  pull_request:
    if: github.event.pull_request.head.repo.fork == false  # ❌ ERROR

# ✅ CORRECT:
on:
  push:
  pull_request:

jobs:
  build:
    if: |
      github.repository == 'owner/repo' &&
      (github.event_name == 'push' || 
       github.event.pull_request.head.repo.fork == false)
    runs-on: ubuntu-latest
```
"""

# ==============================================================================
# Defense Rule 2: NO `timeout-minutes` for Reusable Workflows
# ==============================================================================

DEFENSE_RULE_2_NO_TIMEOUT_REUSABLE = """
#### Defense Rule 2: 🚫 NO `timeout-minutes` for Reusable Workflows
- **ERROR:** `when a reusable workflow is called... timeout-minutes is not available`
- **Rule:** If a job uses `uses: ./.github/workflows/...`, DO NOT add `timeout-minutes`.
- **Exception Handling:** When fixing Smell 5 (Missing Timeout), CHECK if job is reusable first.
```yaml
# ❌ WRONG (Reusable Workflow):
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR - not allowed for reusable workflows

# ✅ CORRECT:
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml  # ✅ No timeout for reusable

  regular-job:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # ✅ OK for regular jobs
```
"""

# ==============================================================================
# Defense Rule 3: Strict List Syntax for Paths/Branches
# ==============================================================================

DEFENSE_RULE_3_STRICT_LIST_SYNTAX = """
#### Defense Rule 3: 📝 Strict List Syntax for Paths/Branches
- **ERROR:** `expected scalar node ... but found sequence node`
- **Rule:** `paths`, `paths-ignore`, `branches`, `branches-ignore` MUST use list format (hyphens).
```yaml
# ❌ WRONG:
on:
  push:
    paths-ignore: '**.md'  # ❌ Single string - may cause errors

# ✅ CORRECT (Use List Format):
on:
  push:
    paths-ignore:
      - '**.md'      # ✅ List item (note the hyphen)
      - 'docs/**'    # ✅ Each pattern on separate line
```
"""

# ==============================================================================
# Defense Rule 4: Separation of `uses` and `run`
# ==============================================================================

DEFENSE_RULE_4_SEPARATE_USES_RUN = """
#### Defense Rule 4: 🧩 Separation of `uses` and `run`
- **ERROR:** `step contains both "uses" and "run"`
- **Rule:** A step CANNOT have both `uses:` (action) and `run:` (shell command).
- **Fix:** Split into two separate steps.
```yaml
# ❌ WRONG:
- name: Checkout and build
  uses: actions/checkout@v4
  run: npm install  # ❌ Cannot coexist

# ✅ CORRECT:
- name: Checkout
  uses: actions/checkout@v4
- name: Build
  run: npm install
```
"""

# ==============================================================================
# Defense Rule 5: Correct Context Usage in Templates (DEPRECATED - USE RULE 10)
# ==============================================================================


# ==============================================================================
# Combined Defense Rules
# ==============================================================================

ALL_DEFENSE_RULES = f"""
### 🛡️ ACTIONLINT & SCHEMA DEFENSE RULES (STRICT) 🛡️
You MUST follow these rules to pass 'actionlint' validation and GitHub Actions schema constraints.

{DEFENSE_RULE_1_NO_IF_IN_TRIGGERS}

{DEFENSE_RULE_2_NO_TIMEOUT_REUSABLE}

{DEFENSE_RULE_3_STRICT_LIST_SYNTAX}

{DEFENSE_RULE_4_SEPARATE_USES_RUN}

"""

# For Semantic Repair (includes Defense Rule 0)
ALL_DEFENSE_RULES_WITH_RULE_0 = f"""
### 🛡️ ACTIONLINT & SCHEMA DEFENSE RULES (STRICT) 🛡️
You MUST follow these rules to pass 'actionlint' validation and GitHub Actions schema constraints.

{DEFENSE_RULE_0_NO_DUPLICATE_KEYS}

{DEFENSE_RULE_1_NO_IF_IN_TRIGGERS}

{DEFENSE_RULE_2_NO_TIMEOUT_REUSABLE}

{DEFENSE_RULE_3_STRICT_LIST_SYNTAX}

{DEFENSE_RULE_4_SEPARATE_USES_RUN}

"""
