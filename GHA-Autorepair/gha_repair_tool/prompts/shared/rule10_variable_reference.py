"""
Rule 10: Variable and Context Reference Guide
Based on GitHub Actions official documentation
"""

YAML_RULE_10_VARIABLE_REFERENCE = """
#### Rule 10: 📚 Variable and Context Reference Guide

This guide helps you use GitHub Actions contexts correctly. All examples are from the official GitHub documentation.

**Reference:** https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/contexts

---

### A. Understanding Contexts

GitHub Actions provides several contexts to access information during workflow execution. 
Each context has specific properties you can reference using `${{ context.property }}` syntax.

**Available Contexts:**
- `github.*` - Workflow run information (workspace, ref, sha, etc.)
- `env.*` - Environment variables you define
- `inputs.*` - Workflow inputs (workflow_call, workflow_dispatch)
- `matrix.*` - Matrix strategy values
- `steps.*` - Outputs from previous steps
- `needs.*` - Outputs from dependent jobs
- `runner.*` - Runner environment (os, arch, temp, etc.)
- `secrets.*` - Repository and organization secrets
- `job.*` - Current job information
- `vars.*` - Configuration variables

---

### B. Context Examples (From Official Docs)

#### 1️⃣ **github context** - Workflow metadata

```yaml
# Example: Access workspace directory
name: Build
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Workspace: ${{ github.workspace }}"
      - run: echo "Repository: ${{ github.repository }}"
      - run: echo "Branch: ${{ github.ref }}"
```

**Common properties:**
- `github.workspace` - `/home/runner/work/repo/repo`
- `github.repository` - `owner/repo-name`
- `github.ref` - `refs/heads/main`
- `github.sha` - Commit SHA
- `github.actor` - Username who triggered

---

#### 2️⃣ **env context** - Environment variables

```yaml
# Example: Using environment variables at different levels
name: Hi Mascot
on: push
env:
  mascot: Mona              # Workflow level
  super_duper_var: totally_awesome

jobs:
  windows_job:
    runs-on: windows-latest
    steps:
      - run: echo 'Hi ${{ env.mascot }}'  # Hi Mona
      - run: echo 'Hi ${{ env.mascot }}'  # Hi Octocat
        env:
          mascot: Octocat   # Step level (overrides workflow level)
  
  linux_job:
    runs-on: ubuntu-latest
    env:
      mascot: Tux           # Job level
    steps:
      - run: echo 'Hi ${{ env.mascot }}'  # Hi Tux
```

**Key point:** More specific env overrides less specific (step > job > workflow)

---

#### 3️⃣ **inputs context** - Workflow inputs

**For workflow_dispatch (manual trigger):**
```yaml
on:
  workflow_dispatch:
    inputs:
      build_id:
        required: true
        type: string
      deploy_target:
        required: true
        type: string
      perform_deploy:
        required: true
        type: boolean

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ inputs.perform_deploy }}
    steps:
      - run: echo "Deploying build:${{ inputs.build_id }} to target:${{ inputs.deploy_target }}"
```

**For workflow_call (reusable workflows):**
```yaml
name: Reusable deploy workflow
on:
  workflow_call:
    inputs:
      build_id:
        required: true
        type: number
      deploy_target:
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying build:${{ inputs.build_id }} to target:${{ inputs.deploy_target }}"
```

**Important:** \`inputs\` are defined INSIDE \`workflow_dispatch:\` or \`workflow_call:\`, not at workflow root level.

---

#### 4️⃣ **matrix context** - Matrix strategy values

```yaml
# Example: Using matrix values
name: Test matrix
on: push

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        node: [14, 16]
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: node --version
```

**Reference:** Values defined in \`strategy.matrix\` are accessed via \`matrix.property_name\`

---

#### 5️⃣ **steps context** - Step outputs

```yaml
# Example: Passing data between steps
name: Generate random failure
on: push
jobs:
  randomly-failing-job:
    runs-on: ubuntu-latest
    steps:
      - name: Generate 0 or 1
        id: generate_number
        run: echo "random_number=$(($RANDOM % 2))" >> $GITHUB_OUTPUT
      
      - name: Pass or fail
        run: |
          if [[ ${{ steps.generate_number.outputs.random_number }} == 0 ]]; then 
            exit 0
          else 
            exit 1
          fi
```

**Pattern:** \`steps.<step_id>.outputs.<output_name>\`

**Requirements:**
- Step must have an \`id\`
- Output must be set with \`>> $GITHUB_OUTPUT\`
- Step must run before being referenced

---

#### 6️⃣ **needs context** - Job dependencies

```yaml
# Example: Using outputs from dependent jobs
name: Build and deploy
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      build_id: ${{ steps.build_step.outputs.build_id }}
    steps:
      - name: Build
        id: build_step
        run: echo "build_id=$RANDOM" >> $GITHUB_OUTPUT
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying build ${{ needs.build.outputs.build_id }}"
  
  debug:
    needs: [build, deploy]
    runs-on: ubuntu-latest
    if: ${{ failure() }}
    steps:
      - run: echo "Failed to build and deploy"
```

**Pattern:** \`needs.<job_id>.outputs.<output_name>\`

---

#### 7️⃣ **runner context** - Runner environment

```yaml
# Example: Using runner context for temporary files
name: Build
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build with logs
        run: |
          mkdir ${{ runner.temp }}/build_logs
          echo "Logs from building" > ${{ runner.temp }}/build_logs/build.log
      
      - name: Upload logs on fail
        if: ${{ failure() }}
        uses: actions/upload-artifact@v4
        with:
          name: Build failure logs
          path: ${{ runner.temp }}/build_logs
```

**Common properties:**
- \`runner.os\` - \`Linux\`, \`Windows\`, \`macOS\`
- \`runner.arch\` - \`X64\`, \`ARM\`, \`ARM64\`
- \`runner.temp\` - Temporary directory path
- \`runner.tool_cache\` - Pre-installed tools directory

---

### C. Common Mistakes and Fixes

#### ❌ Mistake 1: Using variable without context prefix

```yaml
# WRONG:
env:
  binary_zip: release.zip
steps:
  - run: echo "${{ binary_zip }}"    # ❌ undefined variable "binary_zip"

# CORRECT:
env:
  binary_zip: release.zip
steps:
  - run: echo "${{ env.binary_zip }}"    # ✅ Use env.binary_zip
```

---

#### ❌ Mistake 2: Using \`workspace\` instead of \`github.workspace\`

```yaml
# WRONG:
- run: cd ${{ workspace }}    # ❌ property "workspace" is not defined

# CORRECT:
- run: cd ${{ github.workspace }}    # ✅ github.workspace
```

---

#### ❌ Mistake 3: Matrix value without \`matrix.\` prefix

```yaml
# WRONG:
strategy:
  matrix:
    os: [ubuntu, windows]
runs-on: ${{ os }}    # ❌ undefined variable "os"

# CORRECT:
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
runs-on: ${{ matrix.os }}    # ✅ matrix.os
```

---

#### ❌ Mistake 4: Step output without proper setup

```yaml
# WRONG:
steps:
  - name: Get version
    run: echo "1.0.0"
  - run: echo "${{ version }}"    # ❌ undefined variable "version"

# CORRECT:
steps:
  - name: Get version
    id: version_step
    run: echo "version=1.0.0" >> $GITHUB_OUTPUT    # ✅ Set output
  - run: echo "${{ steps.version_step.outputs.version }}"    # ✅ Reference with full path
```

---

#### ❌ Mistake 5: Inputs at wrong location

```yaml
# WRONG:
name: Release
on: [workflow_dispatch]
inputs:              # ❌ inputs at workflow root level
  version:
    required: true

# CORRECT:
name: Release
on:
  workflow_dispatch:
    inputs:          # ✅ inputs inside workflow_dispatch
      version:
        required: true
        type: string
jobs:
  release:
    steps:
      - run: echo "Version: ${{ inputs.version }}"
```

---

### D. Quick Reference Table

| Context | When to Use | Example |
|---------|-------------|---------|
| \`github.*\` | Built-in workflow metadata | \`\${{ github.workspace }}\` |
| \`env.*\` | Custom environment variables | \`\${{ env.VERSION }}\` |
| \`inputs.*\` | Workflow/reusable workflow inputs | \`\${{ inputs.deploy_target }}\` |
| \`matrix.*\` | Matrix strategy values | \`\${{ matrix.node }}\` |
| \`steps.*\` | Previous step outputs | \`\${{ steps.build.outputs.version }}\` |
| \`needs.*\` | Dependent job outputs | \`\${{ needs.build.outputs.artifact }}\` |
| \`runner.*\` | Runner environment info | \`\${{ runner.os }}\` |
| \`secrets.*\` | Repository secrets | \`\${{ secrets.GITHUB_TOKEN }}\` |

---

### E. Troubleshooting Guide

**If you see: \`undefined variable "X"\`**
→ Check if you need: \`env.X\`, \`matrix.X\`, \`inputs.X\`, or \`github.X\`

**If you see: \`property "X" is not defined\`**
→ Common fixes:
  - \`workspace\` → \`github.workspace\`
  - \`os\` (in matrix) → \`matrix.os\`
  - Step output → Add step \`id\` and use \`steps.<id>.outputs.X\`

**If you see: \`available variables are "env", "github"...\`**
→ You're using a variable name directly, need to add context prefix

---

"""
