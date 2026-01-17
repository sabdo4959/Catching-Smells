"""
Rule 10: Variable and Property Reference Validation
"""

YAML_RULE_10_VARIABLE_REFERENCE = """
#### Rule 10: Variable and Property Reference Validation

**CRITICAL: All variables and properties MUST be defined before use!**

---

### A. UNDEFINED VARIABLE ERRORS

**Common Pattern: `undefined variable "variable_name"`**

This error means you're using `${{ variable_name }}` but it's not defined anywhere.

**Available Variable Contexts:**
- `env.*` - Environment variables (workflow/job/step level)
- `github.*` - GitHub context (github.workspace, github.sha, github.ref, etc.)
- `secrets.*` - Repository secrets
- `inputs.*` - Workflow inputs (workflow_call, workflow_dispatch)
- `matrix.*` - Matrix variables (when using strategy.matrix)
- `needs.<job_id>.outputs.*` - Outputs from previous jobs
- `steps.<step_id>.outputs.*` - Outputs from previous steps
- `runner.*` - Runner context (runner.os, runner.arch, runner.workspace, etc.)

---

### B. FIX STRATEGY FOR UNDEFINED VARIABLES

**Case 1: Variable used but never defined**

❌ WRONG:
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Use variable
        run: echo "${{ binary_zip }}"    # ❌ undefined variable "binary_zip"
```

**Fix Options:**

**Option A: Define in `env`**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      binary_zip: release.zip    # ✅ Define here
    steps:
      - name: Use variable
        run: echo "${{ env.binary_zip }}"    # ✅ Now reference with env. prefix
```

**Option B: Set as step output**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Create variable
        id: setup
        run: echo "binary_zip=release.zip" >> $GITHUB_OUTPUT    # ✅ Define output
      
      - name: Use variable
        run: echo "${{ steps.setup.outputs.binary_zip }}"    # ✅ Reference output
```

**Option C: Use from GitHub context (if appropriate)**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Use GitHub variable
        run: echo "${{ github.workspace }}"    # ✅ Built-in context
```

---

### C. PROPERTY NOT DEFINED ERRORS

**Common Pattern: `property "property_name" is not defined in object type {}`**

This means you're accessing `object.property` but the property doesn't exist.

**Most Common Cases:**

**Case 1: `workspace` property**

❌ WRONG:
```yaml
- run: cd ${{ workspace }}    # ❌ property "workspace" is not defined
```

✅ CORRECT:
```yaml
- run: cd ${{ github.workspace }}    # ✅ Use github.workspace
# OR
- run: cd ${{ runner.workspace }}     # ✅ Use runner.workspace (parent dir)
```

**Case 2: Step outputs (`version`, `release`, `changelog`, etc.)**

❌ WRONG:
```yaml
steps:
  - name: Get version
    id: version_step
    run: echo "1.0.0"
  
  - name: Use version
    run: echo "${{ version }}"    # ❌ property "version" is not defined
```

✅ CORRECT:
```yaml
steps:
  - name: Get version
    id: version_step
    run: echo "version=1.0.0" >> $GITHUB_OUTPUT    # ✅ Set output properly
  
  - name: Use version
    run: echo "${{ steps.version_step.outputs.version }}"    # ✅ Full path
```

**Case 3: Matrix properties**

❌ WRONG:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
steps:
  - run: echo "${{ operating_system }}"    # ❌ undefined variable
```

✅ CORRECT:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
steps:
  - run: echo "${{ matrix.os }}"    # ✅ Use matrix.os
```

---

### D. COMMON VARIABLE PATTERNS

**Pattern 1: Environment Variables**
```yaml
env:
  VERSION: "1.0.0"
  BINARY_ZIP: "release.zip"

jobs:
  build:
    steps:
      - run: echo "${{ env.VERSION }}"        # ✅ Workflow-level env
      - run: echo "${{ env.BINARY_ZIP }}"     # ✅ Workflow-level env
```

**Pattern 2: Step Outputs Chain**
```yaml
steps:
  - name: Build
    id: build
    run: |
      echo "artifact_name=myapp.zip" >> $GITHUB_OUTPUT
      echo "version=1.0.0" >> $GITHUB_OUTPUT
  
  - name: Upload
    uses: actions/upload-artifact@v3
    with:
      name: ${{ steps.build.outputs.artifact_name }}    # ✅ Reference output
      path: ./dist
  
  - name: Tag release
    run: |
      git tag v${{ steps.build.outputs.version }}       # ✅ Reference output
```

**Pattern 3: Job Outputs**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.get_version.outputs.version }}    # ✅ Expose as job output
    steps:
      - id: get_version
        run: echo "version=1.0.0" >> $GITHUB_OUTPUT
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.version }}"    # ✅ Use job output
```

---

### E. DETECTION AND FIX CHECKLIST

**When you see undefined variable/property errors:**

1. **Identify the variable**: What is being referenced?
   - `${{ binary_zip }}` → variable: `binary_zip`
   - `${{ workspace }}` → variable: `workspace`
   - `${{ version }}` → variable: `version`

2. **Determine correct context**:
   - Is it a file path? → Use `github.workspace`
   - Is it a custom value? → Define in `env` or step output
   - Is it from another step? → Use `steps.<id>.outputs.*`
   - Is it from matrix? → Use `matrix.*`

3. **Add definition**:
   - Add to `env:` section
   - Or set in previous step with `>> $GITHUB_OUTPUT`
   - Or use correct built-in context (github.*, runner.*, etc.)

4. **Update all references**:
   - Change `${{ variable }}` to `${{ env.variable }}`
   - Or change to `${{ steps.step_id.outputs.variable }}`
   - Or change to `${{ github.property }}`

---

### F. CRITICAL GITHUB CONTEXTS REFERENCE

**Commonly Used Properties:**

```yaml
# GitHub Context
${{ github.workspace }}      # Working directory (e.g., /home/runner/work/repo/repo)
${{ github.repository }}     # owner/repo-name
${{ github.ref }}            # refs/heads/main
${{ github.sha }}            # Commit SHA
${{ github.actor }}          # Username who triggered
${{ github.event_name }}     # Event type (push, pull_request, etc.)

# Runner Context
${{ runner.os }}             # Linux, Windows, macOS
${{ runner.arch }}           # X64, ARM, ARM64
${{ runner.workspace }}      # Parent directory of github.workspace
${{ runner.temp }}           # Temp directory path

# Job Context
${{ job.status }}            # success, failure, cancelled

# Steps Context (requires step id)
${{ steps.<step_id>.outputs.<output_name> }}
${{ steps.<step_id>.outcome }}    # success, failure, cancelled, skipped
${{ steps.<step_id>.conclusion }} # success, failure, cancelled, skipped, neutral

# Needs Context (requires job dependency)
${{ needs.<job_id>.outputs.<output_name> }}
${{ needs.<job_id>.result }}      # success, failure, cancelled, skipped

# Matrix Context (requires strategy.matrix)
${{ matrix.<key> }}              # Value from matrix
```

---

### G. VALIDATION RULES SUMMARY

**BEFORE generating YAML:**

1. ✅ Every `${{ variable }}` must have a corresponding definition
2. ✅ Use correct context prefix: `env.`, `steps.`, `github.`, `runner.`, `matrix.`, `needs.`
3. ✅ Define variables BEFORE using them (in `env` or previous steps)
4. ✅ Use `>> $GITHUB_OUTPUT` for step outputs, not just `echo`
5. ✅ Reference workspace as `github.workspace`, not `workspace`
6. ✅ Chain step outputs with full path: `steps.<id>.outputs.<name>`

**AFTER generating YAML:**

1. ✅ Search for all `${{ ... }}` expressions
2. ✅ Verify each variable/property is defined
3. ✅ Check context prefixes are correct
4. ✅ Ensure output chains are valid (step id exists, output name matches)

---

### H. COMPLETE EXAMPLE: BEFORE & AFTER

**❌ WRONG (Multiple undefined variable errors):**
```yaml
name: Build

on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build
        run: |
          echo "Building version ${{ VERSION }}"              # ❌ undefined variable "VERSION"
          zip -r ${{ binary_zip }} ./dist                     # ❌ undefined variable "binary_zip"
          echo "Workspace: ${{ workspace }}"                  # ❌ property "workspace" not defined
      
      - name: Upload
        uses: actions/upload-artifact@v3
        with:
          name: ${{ artifact_name }}                          # ❌ undefined variable "artifact_name"
          path: ./dist
      
      - name: Create release
        run: |
          gh release create v${{ version }} \\                # ❌ property "version" not defined
            --notes "${{ changelog }}"                        # ❌ property "changelog" not defined
```

**✅ CORRECT (All variables properly defined):**
```yaml
name: Build

on: push

env:
  VERSION: "1.0.0"                           # ✅ Define at workflow level
  BINARY_ZIP: "release.zip"                  # ✅ Define at workflow level

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build
        id: build_step                       # ✅ Add ID for outputs
        run: |
          echo "Building version ${{ env.VERSION }}"           # ✅ Use env.VERSION
          zip -r ${{ env.BINARY_ZIP }} ./dist                  # ✅ Use env.BINARY_ZIP
          echo "Workspace: ${{ github.workspace }}"            # ✅ Use github.workspace
          
          # Set outputs for next steps
          echo "artifact_name=${{ env.BINARY_ZIP }}" >> $GITHUB_OUTPUT    # ✅ Define output
          echo "version=${{ env.VERSION }}" >> $GITHUB_OUTPUT             # ✅ Define output
          echo "changelog=Initial release" >> $GITHUB_OUTPUT              # ✅ Define output
      
      - name: Upload
        uses: actions/upload-artifact@v3
        with:
          name: ${{ steps.build_step.outputs.artifact_name }}  # ✅ Use step output
          path: ./dist
      
      - name: Create release
        run: |
          gh release create v${{ steps.build_step.outputs.version }} \\    # ✅ Use step output
            --notes "${{ steps.build_step.outputs.changelog }}"            # ✅ Use step output
```

---

### I. ACTIONLINT ERROR MESSAGES → FIXES

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `undefined variable "X"` | Using `${{ X }}` without definition | Add to `env:` or define in previous step output |
| `property "X" is not defined` | Using `${{ obj.X }}` where X doesn't exist | Use correct property name or define in step output |
| `available variables are "env", "github"...` | Variable not in any context | Use correct context prefix (env., github., etc.) |
| `object type {}` | Trying to access property on empty/undefined object | Define the object first with step outputs |

---

**REMEMBER: GitHub Actions expressions are STRICTLY TYPED. Every variable must be explicitly defined!**
"""
