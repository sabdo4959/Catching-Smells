"""
YAML Generation Rules - Syntax Constraints

These rules ensure the LLM generates valid YAML that passes GitHub Actions validation.
Shared between Syntax and Semantic repair phases.

Version History:
- v1.0: Initial rules 1-5 (Quote wildcards, Block scalar, Quote if, Indentation, No markdown)
- v2.0: Added rules 6-8 (Concurrency placement, No duplicate keys, Structure types)
- v3.0: Added rules 8E-8G (Filter nesting, Remove empty, Action inputs)
- v3.1: Added Rule 9 (Job structure validation)
- v3.2: Added Rule 10 (Variable and property reference validation)

References:
- YAML Specification: https://yaml.org/spec/1.2/spec.html
- GitHub Actions Syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
"""

# Import Rule 10 from separate file
from .rule10_variable_reference import YAML_RULE_10_VARIABLE_REFERENCE


# ==============================================================================
# YAML Generation Rules (Core)
# ==============================================================================

YAML_RULE_1_QUOTE_WILDCARDS = """
#### Rule 1: Quote Wildcards and Globs
- **ALWAYS quote** strings containing wildcards: `*`, `?`, `[`, `]`
- Examples:
  - ❌ Bad: `files: *.whl`
  - ✅ Good: `files: '*.whl'`
"""

YAML_RULE_2_FORCE_BLOCK_SCALAR = """
#### Rule 2: FORCE Block Scalar (`|`) for `run` with Special Cases
- You **MUST** use the pipe (`|`) style when `run` contains:
  1. A colon (`:`) followed by a space
  2. Blank/empty lines between commands (including after comments)
  3. Multi-line commands
- Quoting is NOT enough (it causes YAML parsing conflicts).
- **CRITICAL**: Keep ALL command text exactly the same, only change YAML format.

**CRITICAL EXAMPLES - Learn from these exact patterns:**

**Pattern 1: Colon in run command**
  - ❌ WRONG: `run: echo "binary zip: ${{ binary_zip }}"`
  - ❌ WRONG: `run: 'echo "Status: Success"'`
  - ✅ CORRECT:
    ```
    run: |
      echo "binary zip: ${{ binary_zip }}"
    ```

**Pattern 2: Blank lines in run (especially after comments)**
  - ❌ WRONG:
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      
      if [ condition ]; then
    ```
  - ✅ CORRECT (remove blank lines after comments):
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      if [ condition ]; then
    ```

**Pattern 3: Multi-line with colons AND blank lines**
  - ❌ WRONG: Any run with both issues without `|`
  - ✅ CORRECT: Always use `run: |` and clean up blank lines after comments
"""

YAML_RULE_3_QUOTE_IF_CONDITIONS = """
#### Rule 3: QUOTE ENTIRE `if` Conditions with Colons
- If an `if` expression contains a colon (e.g., inside a string like `'type: bug'`), quote the **WHOLE** condition.
- Examples:
  - ❌ Bad: `if: github.event.label.name == 'type: bug'`
  - ✅ Good: `if: "github.event.label.name == 'type: bug'"`
"""

YAML_RULE_4_STRICT_INDENTATION = """
#### Rule 4: Strict Indentation (2 Spaces)
- Use **exactly 2 spaces** per level. NO TABS.
- Content inside `|` block must be indented **2 spaces deeper** than the parent key.
- Examples:
  - ❌ Bad:
    ```
    run: |
    echo "no indent"
    ```
  - ✅ Good:
    ```
    run: |
      echo "proper indent"
    ```
"""

YAML_RULE_5_NO_MARKDOWN = """
#### Rule 5: NO MARKDOWN FENCES OR BACKTICKS (CRITICAL - NEW)
- **ABSOLUTELY FORBIDDEN:** Backtick characters (`, ```, ``````) in YAML output
- **DO NOT** use markdown code block syntax anywhere in the YAML
- **VERIFICATION:** Output must NOT contain ANY backtick (`) character
- **Common Error:** found character backtick that cannot start any token
- Examples:
  - ❌ WRONG: run with backtick characters
  - ❌ WRONG: Including markdown code fences in output
  - ✅ CORRECT: Use $() for command substitution instead of backticks
- **Return RAW YAML TEXT ONLY** without any markdown formatting.
"""

YAML_RULE_6_CONCURRENCY_PLACEMENT = """
#### Rule 6: `concurrency` Placement Rules (FIX COMMON ERROR)
- **ERROR PATTERN:** `unexpected key "concurrency" for "push" section` or `"pull_request" section`
- **ROOT CAUSE:** `concurrency` placed INSIDE trigger sections instead of at workflow/job level
- **RULE:** `concurrency` is ONLY valid at:
  1. **Workflow-level** (root of YAML, alongside `name:`, `on:`)
  2. **Job-level** (inside a job definition, alongside `runs-on:`, `steps:`)
- **NEVER place `concurrency` inside:**
  - ❌ `on:` section
  - ❌ `on.push:` section  
  - ❌ `on.pull_request:` section
  - ❌ `on.workflow_dispatch:` section
  - ❌ Any trigger configuration

**EXAMPLES:**

**❌ WRONG - concurrency inside trigger:**
```yaml
on:
  push:
    branches: [main]
    concurrency:        # ❌ INVALID - cannot be inside push
      group: build
      cancel-in-progress: true
```

**❌ WRONG - concurrency as job name:**
```yaml
jobs:
  concurrency:          # ❌ INVALID - job named 'concurrency' 
    group: test         # ❌ Missing runs-on, steps
    cancel-in-progress: true
```

**✅ CORRECT - Workflow-level concurrency:**
```yaml
name: CI
on:
  push:
    branches: [main]

concurrency:            # ✅ VALID - at workflow root
  group: ${{{{ github.workflow }}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**✅ CORRECT - Job-level concurrency:**
```yaml
name: CI
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    concurrency:        # ✅ VALID - inside job
      group: build-${{{{ github.ref }}}}
      cancel-in-progress: true
    steps:
      - run: npm install
```

**FIX STRATEGY:**
1. **DETECT:** Find `concurrency:` inside `on:` or trigger sections
2. **EXTRACT:** Remove `concurrency:` block from wrong location
3. **RELOCATE:** Move to workflow root (before `jobs:`) or inside specific job
4. **VERIFY:** Ensure `group:` and `cancel-in-progress:` remain intact
"""

YAML_RULE_7_NO_DUPLICATE_KEYS = """
#### Rule 7: NO Duplicate Keys - Merge Strategy (CRITICAL) 👯
- **FATAL ERROR:** `key "jobs" is duplicated`, `key "on" is duplicated`, `key "env" is duplicated`, `key "permissions" is duplicated`
- **Official Syntax:** Per YAML spec and GitHub Actions syntax, a mapping CANNOT contain duplicate keys at the same level
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **ROOT CAUSE:** Appending new content at end of file instead of merging into EXISTING blocks
- **STRICT INSTRUCTION:**
  1. **CHECK:** Does the top-level key (`jobs`, `on`, `permissions`, `env`, `concurrency`) ALREADY EXIST in the file?
  2. **IF EXISTS:** Write new content **INSIDE** the existing block (merge, don't duplicate)
  3. **NEVER:** Write the same top-level key twice

**EXAMPLES:**

**❌ WRONG - Duplicate 'jobs' key:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build

# ... lines later ...
jobs:                    # ❌ DUPLICATE KEY ERROR!
  test:
    runs-on: ubuntu-latest
```

**✅ CORRECT - Merged into single 'jobs' block:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build
  test:                  # ✅ Added as sibling job (same indentation as 'build')
    runs-on: ubuntu-latest
```

**❌ WRONG - Duplicate 'on' key:**
```yaml
on:
  push:
    branches: [main]

on:                      # ❌ DUPLICATE KEY ERROR!
  pull_request:
    branches: [main]
```

**✅ CORRECT - Merged triggers:**
```yaml
on:
  push:
    branches: [main]
  pull_request:          # ✅ Added as sibling trigger (same level as 'push')
    branches: [main]
```

**FIX STRATEGY:**
1. **SCAN:** Identify ALL occurrences of top-level keys (`jobs:`, `on:`, `env:`, etc.)
2. **MERGE:** Combine all content under the FIRST occurrence
3. **DELETE:** Remove duplicate key declarations
4. **VERIFY:** Maintain proper indentation (siblings at same level)
"""

YAML_RULE_8_STRUCTURE_TYPES = """
#### Rule 8: YAML Structure Types - Sequence vs. Mapping (CRITICAL) 🏗️
- **FATAL ERRORS:** 
  - `"push" section is sequence node but mapping node is expected`
  - `"tags" section is sequence node but mapping node is expected`
  - `expected scalar node for string value but found sequence node`
- **Official Syntax:** GitHub Actions has STRICT requirements for Mappings (key-value) vs. Sequences (lists)
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **ROOT CAUSE:** Using list syntax (`- item`) where key-value pairs are required, or vice versa

**A. Areas Requiring MAPPINGS (Key-Value, NO Dashes `-`):**

1. **`jobs:`** - Job names are keys, not list items
   - ✅ CORRECT: `jobs:\\n  build:\\n    runs-on: ubuntu-latest`
   - ❌ WRONG: `jobs:\\n  - build:` (don't use dash)

2. **`on:`** - Event names are keys
   - ✅ CORRECT: `on:\\n  push:\\n    branches: [main]`
   - ❌ WRONG: `on:\\n  - push:` (don't use dash)

3. **`on.push:`, `on.pull_request:`** - Trigger filters are keys
   - ✅ CORRECT: `push:\\n  branches: [main]\\n  tags: [v*]`
   - ❌ WRONG: `push:\\n  - branches: [main]` (don't use dash before branches)

4. **`env:`** - Environment variables are key-value pairs
   - ✅ CORRECT: `env:\\n  NODE_VERSION: '14'`
   - ❌ WRONG: `env:\\n  - NODE_VERSION: '14'`

5. **`with:`** - Action inputs are key-value pairs
   - ✅ CORRECT: `with:\\n  node-version: 14`
   - ❌ WRONG: `with:\\n  - node-version: 14`

**B. Areas Requiring SEQUENCES (List, MUST use Dashes `-`):**

1. **`steps:`** - Steps are ALWAYS a list
   - ✅ CORRECT: `steps:\\n  - name: Checkout\\n    uses: actions/checkout@v4`
   - ❌ WRONG: `steps:\\n  name: Checkout` (missing dash)

2. **`branches:`, `tags:`, `paths:`** - Filter values are lists (when multiple items)
   - ✅ CORRECT: `branches:\\n  - main\\n  - develop` OR `branches: [main, develop]`
   - ✅ ALSO OK: `branches: main` (single scalar value allowed)
   - ❌ WRONG: Empty without values (see Rule 8F)

3. **`types:`** - Event types are lists
   - ✅ CORRECT: `types: [opened, synchronize]` OR `types:\\n  - opened\\n  - synchronize`

4. **`strategy.matrix:`** - Matrix values are lists
   - ✅ CORRECT: `matrix:\\n  node-version: [14, 16, 18]`

**C. Special Rules:**

1. **`needs:`** - Can be scalar (string) OR sequence (list), NEVER mapping
   - ✅ CORRECT: `needs: build`
   - ✅ CORRECT: `needs: [build, test]`
   - ❌ WRONG: `needs:\\n  build: true`

2. **`secrets:`** - For reusable workflows, can be mapping OR `inherit` keyword
   - ✅ CORRECT: `secrets:\\n  TOKEN: ${{{{ secrets.TOKEN }}}}`
   - ✅ CORRECT: `secrets: inherit`
   - ❌ WRONG: `secrets:\\n  - TOKEN: value` (not a list)

3. **Empty sections MUST be removed:**
   - ❌ WRONG: `tags:` (no values)
   - ❌ WRONG: `env:` (no variables)
   - ❌ WRONG: `paths-ignore:` (no paths)
   - ✅ CORRECT: Remove the entire empty section

**D. Structure Conversion Patterns (CRITICAL FIXES):**

1. **Shorthand to Full Syntax (Triggers):**
   - ❌ WRONG: `on: [push]` → `push: []` (Empty list is wrong)
   - ❌ WRONG: `on: [push]` → `push: {}` (Empty mapping at root is wrong)
   - ✅ CORRECT: `on: [push]` → `on:\\n  push:` (Mapping inside 'on')
   
   - ❌ WRONG: `on: [push, pull_request]` → `push: []\\n  pull_request: []`
   - ✅ CORRECT: `on: [push, pull_request]` → `on:\\n  push:\\n  pull_request:`

2. **Filter Placement (Nesting Rule):**
   - **Rule:** `tags`, `branches`, `paths`, `paths-ignore` MUST be INSIDE a specific trigger (push/pull_request), NOT directly under `on`.
   - ❌ WRONG (tags as sibling to push):
     ```yaml
     on:
       push:
         branches: [main]
       tags: [v*]  # ❌ Error: tags is at wrong level
     ```
   - ✅ CORRECT (tags nested in push):
     ```yaml
     on:
       push:
         branches: [main]
         tags: [v*]  # ✅ Correct: tags is child of push
     ```
   - ❌ WRONG (tags at on level):
     ```yaml
     on:
       push:
       tags:  # ❌ Error: tags should be inside push
         - v*
     ```
   - ✅ CORRECT (move tags into push):
     ```yaml
     on:
       push:
         tags:  # ✅ Correct: tags is inside push
           - v*
     ```

**EXAMPLES:**

**❌ WRONG - push as sequence:**
```yaml
on:
  - push:                # ❌ push should be a KEY, not a list item
      branches: [main]
```

**✅ CORRECT - push as mapping:**
```yaml
on:
  push:                  # ✅ push is a key (no dash)
    branches: [main]
```

**❌ WRONG - tags empty:**
```yaml
on:
  push:
    tags:                # ❌ Empty - must have values or be removed
```

**✅ CORRECT - tags with values or removed:**
```yaml
on:
  push:
    tags:
      - v*               # ✅ List of tag patterns
      - release-*
```
OR
```yaml
on:
  push:
    branches: [main]     # ✅ Removed empty tags section entirely
```

**FIX STRATEGY:**
1. **IDENTIFY:** Check GitHub Actions syntax reference for expected type (mapping vs. sequence)
2. **CONVERT:** 
   - If mapping needed → Remove dashes, use `key: value` format
   - If sequence needed → Add dashes, use `- item` format or `[item1, item2]`
3. **REMOVE:** Delete any empty sections (no values)
4. **VERIFY:** Check indentation matches the structure type
"""

# ==============================================================================
# NEW Rules (v3.0)
# ==============================================================================

YAML_RULE_8E_FILTER_NESTING = """
**E. Filter Nesting (tags, branches, paths) 🏗️ - NEW v3**

- **CRITICAL RULE:** `tags`, `branches`, `paths`, `paths-ignore` MUST be nested INSIDE their trigger event
- **NEVER** place as sibling to `push`/`pull_request` at `on:` level
- **ROOT CAUSE:** LLM places filters at wrong indentation level

**LOCATION HIERARCHY:**
```
on:                      # Level 0: Workflow triggers
  push:                  # Level 1: Event type (mapping key, no dash)
    branches:            # Level 2: Event filter (must be inside push)
      - main             # Level 3: Filter values (list)
    tags:                # Level 2: Event filter (must be inside push)
      - v*               # Level 3: Filter values (list)
  pull_request:          # Level 1: Another event (sibling to push)
    branches:            # Level 2: Filter (must be inside pull_request)
      - main
```

**❌ WRONG - tags as sibling to push:**
```yaml
on:
  push:
    branches: [main]
  tags:                  # ❌ ERROR: tags is at same level as push
    - v*
  pull_request:
```

**✅ CORRECT - tags nested inside push:**
```yaml
on:
  push:
    branches: [main]
    tags:                # ✅ Correct: tags is INSIDE push
      - v*
  pull_request:
```

**❌ WRONG - paths-ignore outside triggers:**
```yaml
on:
  push:
    branches: [main]
  pull_request:
paths-ignore:            # ❌ ERROR: at wrong level
  - '**.md'
```

**✅ CORRECT - paths-ignore inside each trigger:**
```yaml
on:
  push:
    branches: [main]
    paths-ignore:        # ✅ Inside push
      - '**.md'
  pull_request:
    paths-ignore:        # ✅ Inside pull_request
      - '**.md'
```
"""

YAML_RULE_8F_REMOVE_EMPTY = """
**F. Remove Empty Sections 🗑️ - NEW v3**

- **FATAL ERROR:** Empty sections (`key: []`, `key: {}`, `key:` with no value) cause validation errors
- **RULE:** If a section has NO values, REMOVE it entirely (don't create empty list/mapping)
- **COMMON ERRORS:** `tags: []`, `branches: []`, `env: {}`, `steps: []`

**❌ WRONG - Empty sections:**
```yaml
on:
  push:
    tags: []             # ❌ ERROR: Empty list
    branches: []         # ❌ ERROR: Empty list

env: {}                  # ❌ ERROR: Empty mapping

jobs:
  build:
    env:                 # ❌ ERROR: Empty (no variables)
    steps: []            # ❌ ERROR: Job with no steps
```

**✅ CORRECT - Remove empty sections entirely:**
```yaml
on:
  push:
    branches:            # ✅ Only include sections with actual values
      - main
    # tags removed entirely (was empty)

# env removed entirely (was empty)

jobs:
  build:
    # env removed (was empty)
    steps:               # ✅ Must have at least one step
      - run: echo "test"
```

**DETECTION STRATEGY:**
1. After generating YAML, mentally scan for:
   - `key: []` (empty list)
   - `key: {}` (empty mapping)
   - `key:` followed by next key at same indentation (empty mapping)
2. REMOVE the entire key-value pair
3. Ensure proper indentation after removal
4. **EXCEPTION:** `on.push:` and `on.pull_request:` can be empty (triggers without filters)
"""

YAML_RULE_8G_ACTION_INPUTS = """
**G. Action Input Types (setup-python, setup-node) 🎯 - NEW v3**

- **ERROR PATTERN:** `expected scalar node for string value but found sequence node`
- **ROOT CAUSE:** Providing list `[...]` where action expects single string value
- **COMMON ACTIONS:**
  - `actions/setup-python@v*` → `python-version: 'X.Y'` (scalar, NOT list)
  - `actions/setup-node@v*` → `node-version: 'X'` (scalar, NOT list)
  - `actions/setup-java@v*` → `java-version: 'X'` (scalar, NOT list)

**DECISION LOGIC:**

If you see:
```yaml
with:
  python-version:        # Key exists
    - '3.7'              # ❌ Multiple versions as list
    - '3.8'
    - '3.9'
```

Ask yourself: **Is there a `strategy.matrix` at job level?**

**❌ NO MATRIX → Use latest version only (scalar):**
```yaml
with:
  python-version: '3.9'  # ✅ Latest version (most common case)
```

**✅ YES MATRIX → Reference matrix variable:**
```yaml
strategy:
  matrix:
    python-version: ['3.7', '3.8', '3.9']  # List goes HERE
steps:
  - uses: actions/setup-python@v2
    with:
      python-version: ${{ matrix.python-version }}  # Reference matrix
```

**PRIORITY:** Prefer **single version** (scalar) unless workflow clearly uses matrix strategy elsewhere.

**EXAMPLES:**

**❌ WRONG - List where scalar expected:**
```yaml
- uses: actions/setup-python@v2
  with:
    python-version:
      - '3.8'
      - '3.9'            # ❌ ERROR: List not allowed
```

**✅ CORRECT - Single version:**
```yaml
- uses: actions/setup-python@v2
  with:
    python-version: '3.9'  # ✅ Scalar string
```
"""

YAML_RULE_9_JOB_STRUCTURE = """
**⚠️⚠️⚠️ RULE 9: MANDATORY JOB VALIDATION (READ THIS FIRST!) ⚠️⚠️⚠️**

🚨 **BEFORE YOU OUTPUT ANY YAML, VERIFY THIS:**

Every job under `jobs:` MUST have one of these combinations:
1. `runs-on` + `steps` (regular job) ✅
2. `uses` (reusable workflow) ✅  
3. ANYTHING ELSE = FATAL ERROR ❌

**CRITICALLY IMPORTANT:**
- Job with `runs-on: ubuntu-latest` but NO `steps:` → ❌ INVALID!
- Job with `if: condition` but NO `steps:` → ❌ INVALID!
- Job named "scheduled-job" with `runs-on` but NO `steps:` → ❌ INVALID!

**SELF-CHECK BEFORE OUTPUT:**
□ Did I add `runs-on` to any job?
□ If YES → Did I ALSO add `steps:` with at least ONE step?
□ If NO → STOP and add `steps:` now!

**COMMON FATAL ERRORS TO AVOID:**
- ❌ `"steps" section is missing in job "X"`
- ❌ `"runs-on" section is missing in job "X"`
- ❌ `unexpected key "group"` → This is `concurrency`, not a job!

**DETECTION RULE:** Job with ONLY `group:` + `cancel-in-progress:` → This is `concurrency`, NOT a job!

**A. EVERY JOB MUST HAVE (Mandatory Requirements):**

1. **Regular Job** (most common):
   ```yaml
   jobs:
     build:              # Job ID (any name EXCEPT reserved keywords)
       runs-on: ubuntu-latest   # ✅ REQUIRED
       steps:                   # ✅ REQUIRED (even if just one step)
         - run: echo "test"
   ```

2. **Reusable Workflow Job** (alternative):
   ```yaml
   jobs:
     call-workflow:
       uses: ./.github/workflows/reusable.yml   # ✅ REQUIRED (replaces runs-on + steps)
       secrets: inherit
   ```

3. **FORBIDDEN:** Job with neither `runs-on` + `steps` NOR `uses`
   ```yaml
   jobs:
     incomplete-job:      # ❌ FATAL ERROR: No runs-on, no steps, no uses
       timeout-minutes: 60
       # Missing required keys!
   ```

4. **FORBIDDEN:** Job with `runs-on` but NO `steps`
   ```yaml
   jobs:
     scheduled-job:       # ❌ FATAL ERROR: Has runs-on but missing steps
       if: github.event_name == 'schedule'
       runs-on: ubuntu-latest
       # ❌ Missing: steps section!
   ```
   **FIX:**
   ```yaml
   jobs:
     scheduled-job:       # ✅ CORRECT: Added steps
       if: github.event_name == 'schedule'
       runs-on: ubuntu-latest
       steps:             # ✅ Required!
         - run: echo "Scheduled task"
   ```

**B. RESERVED KEYWORDS CANNOT BE JOB NAMES:**

These are workflow-level or trigger-level keys, NOT job names:
- ❌ `concurrency` (workflow-level keyword)
- ❌ `schedule` (trigger keyword)
- ❌ `on` (workflow-level keyword)
- ❌ `jobs` (workflow-level keyword)
- ❌ `env` (workflow-level keyword)
- ❌ `permissions` (workflow-level keyword)
- ❌ `defaults` (workflow-level keyword)

**DETECTION RULE:** If a "job" ONLY contains `group:` and `cancel-in-progress:` → It's `concurrency`, NOT a job!

**EXAMPLES:**

**❌ WRONG - "concurrency" used as job name:**
```yaml
jobs:
  concurrency:           # ❌ FATAL ERROR: This looks like a job but it's concurrency!
    group: build         # ❌ Job needs runs-on + steps
    cancel-in-progress: true
```

**✅ CORRECT - Move to workflow-level:**
```yaml
concurrency:             # ✅ At workflow root
  group: build
  cancel-in-progress: true

jobs:
  build:                 # ✅ Proper job
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**❌ WRONG - "scheduled-job" without required keys:**
```yaml
jobs:
  scheduled-job:         # ❌ Job name is OK, but missing required keys
    if: github.event_name == 'schedule'
    # Missing: runs-on
    # Missing: steps
```

**✅ CORRECT - Add required keys:**
```yaml
jobs:
  scheduled-job:         # ✅ Job name is fine
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest    # ✅ Added runs-on
    steps:                    # ✅ Added steps
      - run: echo "Scheduled task"
```

**❌ WRONG - Job with only metadata:**
```yaml
jobs:
  deploy:
    timeout-minutes: 60
    environment: production
    # ❌ Missing: runs-on
    # ❌ Missing: steps or uses
```

**✅ CORRECT - Add execution keys:**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest    # ✅ Added runs-on
    timeout-minutes: 60
    environment: production
    steps:                    # ✅ Added steps
      - run: echo "Deploy"
```

**C. SPECIAL CASE: "schedule" Trigger Type Error**

- **ERROR:** `"schedule" section must be sequence node but got mapping node`
- **CAUSE:** Using mapping `{cron: '...'}` instead of list `[{cron: '...'}]`
- **RULE:** `on.schedule` is ALWAYS a list (sequence), even with one cron expression

**❌ WRONG - schedule as mapping:**
```yaml
on:
  schedule:
    cron: '0 0 * * *'    # ❌ ERROR: schedule must be a list
```

**✅ CORRECT - schedule as list:**
```yaml
on:
  schedule:              # ✅ List of cron schedules
    - cron: '0 0 * * *'
```

OR inline list syntax:
```yaml
on:
  schedule: [{cron: '0 0 * * *'}]  # ✅ Also valid (list with one item)
```

**D. FIX STRATEGY (Step-by-step) - MANDATORY CHECKLIST:**

Before outputting the final YAML, mentally execute this checklist:

1. **SCAN** all keys under `jobs:` 
2. **CHECK** each job (one by one):
   - Does it have `runs-on` + `steps`? → ✅ Valid regular job
   - Does it have `uses`? → ✅ Valid reusable workflow job
   - Does it have `runs-on` but NO `steps`? → ❌ FATAL! Add `steps:` with at least one step
   - Does it ONLY have `group` + `cancel-in-progress`? → ❌ This is `concurrency`, move it!
   - Does it have NEITHER? → ❌ Add `runs-on` + `steps` OR remove it
3. **VERIFY** job names don't match reserved keywords (concurrency, schedule, on, jobs, env, permissions, defaults)
4. **RELOCATE** misplaced `concurrency` blocks to workflow-level
5. **ADD** missing `runs-on` and `steps` to incomplete jobs
6. **DOUBLE-CHECK:** Count jobs with `runs-on` → Same count must have `steps` (unless using `uses`)

**CRITICAL REMINDER:** 
- Job with `runs-on: ubuntu-latest` but no `steps:` = INVALID ❌
- Job with `if: condition` but no `steps:` = INVALID ❌  
- **ALWAYS** add `steps:` section when you add `runs-on:`

**E. EDGE CASES:**

1. **Job with conditional execution is still a job:**
   ```yaml
   jobs:
     conditional:
       if: github.event_name == 'push'  # ✅ OK to have if
       runs-on: ubuntu-latest           # ✅ Still needs runs-on
       steps:                           # ✅ Still needs steps
         - run: echo "test"
   ```

2. **Job with matrix strategy is still a job:**
   ```yaml
   jobs:
     matrix-job:
       strategy:
         matrix:
           os: [ubuntu-latest, windows-latest]  # ✅ OK to have strategy
       runs-on: ${{ matrix.os }}                # ✅ Still needs runs-on
       steps:                                   # ✅ Still needs steps
         - run: echo "test"
   ```

3. **Job names CAN be similar to keywords (with different spelling):**
   ```yaml
   jobs:
     scheduled-job: ...   # ✅ OK (not "schedule")
     concurrent-build: ...  # ✅ OK (not "concurrency")
     on-success: ...      # ✅ OK (job name, not trigger "on:")
   ```
"""

# ==============================================================================
# Combined YAML Generation Rules
# ==============================================================================

ALL_YAML_GENERATION_RULES = f"""
### ⚡ IRONCLAD YAML SYNTAX RULES (NO EXCEPTIONS) ⚡
You are a GitHub Actions YAML repair engine. Follow these rules to ensure valid YAML output.

🚨🚨🚨 **CRITICAL: READ RULE 9 FIRST!** 🚨🚨🚨
{YAML_RULE_9_JOB_STRUCTURE}

{YAML_RULE_1_QUOTE_WILDCARDS}

{YAML_RULE_2_FORCE_BLOCK_SCALAR}

{YAML_RULE_3_QUOTE_IF_CONDITIONS}

{YAML_RULE_4_STRICT_INDENTATION}

{YAML_RULE_5_NO_MARKDOWN}

{YAML_RULE_6_CONCURRENCY_PLACEMENT}

{YAML_RULE_7_NO_DUPLICATE_KEYS}

{YAML_RULE_8_STRUCTURE_TYPES}

{YAML_RULE_8E_FILTER_NESTING}

{YAML_RULE_8F_REMOVE_EMPTY}

{YAML_RULE_8G_ACTION_INPUTS}
"""
# Note: YAML_RULE_10_VARIABLE_REFERENCE temporarily excluded for testing
