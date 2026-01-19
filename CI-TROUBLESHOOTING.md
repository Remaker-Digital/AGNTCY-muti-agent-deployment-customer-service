# CI/CD Troubleshooting - Phase 1 Development Workflow

## Current Status (2026-01-19)

### ✅ Passing Jobs
- **code-quality** (ubuntu-latest, Python 3.12) - ✅ Succeeded
- **validate-structure** (ubuntu-latest) - ✅ Succeeded
- **test (ubuntu-latest, 3.12)** - ✅ Succeeded
- **test (ubuntu-latest, 3.13)** - ✅ Succeeded
- **test (macos-latest, 3.12)** - ✅ Succeeded
- **test (macos-latest, 3.13)** - ✅ Succeeded

### ❌ Failing Jobs
- **test (windows-latest, 3.12)** - ❌ Failed (1 annotation)
- **test (windows-latest, 3.13)** - ⚠️ Cancelled (2 annotations)

### ⏭️ Skipped Jobs
- **docker-build** - Skipped (needs all tests to pass)

---

## Root Cause Analysis

### Issue 1: Windows-Specific Test Failures

**Symptoms:**
- Tests pass on Ubuntu and macOS
- Tests fail on Windows (Python 3.12/3.13)
- Local Windows environment (Python 3.14) passes all tests

**Likely Causes:**

1. **Python Version Mismatch**
   - Local: Python 3.14.0
   - CI: Python 3.12/3.13
   - Potential compatibility differences between versions

2. **Path Separator Issues**
   - Windows uses backslashes (`\`) vs Unix forward slashes (`/`)
   - Common in: `get_project_root()`, file path operations
   - Check: `shared/utils.py` path handling

3. **Line Ending Differences**
   - Windows: CRLF (`\r\n`)
   - Unix: LF (`\n`)
   - May affect file-based tests or fixtures

4. **Async/Await Event Loop Issues**
   - Windows has different default event loop behavior
   - `pytest-asyncio` may behave differently on Windows
   - Check: Integration tests using async agents

5. **File Locking**
   - Windows locks files more aggressively than Unix
   - May affect test cleanup or fixture teardown
   - Check: Tests that create/delete files

---

## Diagnostic Steps

### Step 1: Review GitHub Actions Annotations

The workflow shows annotations for:
- `test (windows-latest, 3.13)`: 2 annotations
- `test (windows-latest, 3.12)`: 1 annotation

**Action Required:** Check the GitHub Actions run page for specific error messages.

### Step 2: Reproduce Locally with Python 3.12

```powershell
# Install Python 3.12 alongside 3.14
py -3.12 -m venv venv-py312
.\venv-py312\Scripts\activate
pip install -r requirements.txt
pytest tests/ -v
```

### Step 3: Check Path Handling

Review `shared/utils.py:get_project_root()` for Windows compatibility:

```python
# Current implementation
def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent
```

**Potential Issue:** Path resolution may differ on Windows with OneDrive paths.

### Step 4: Check Async Event Loop Configuration

Review `pytest.ini` async configuration:

```ini
# Current setting
asyncio_mode = auto
```

**Potential Fix:** Explicit event loop policy for Windows:

```python
# In conftest.py or test setup
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

---

## Recommended Fixes

### Fix 1: Update GitHub Actions to Use Python 3.14

**Rationale:** Match CI environment to development environment.

```yaml
# .github/workflows/dev-ci.yml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: ['3.12', '3.13', '3.14']  # Add 3.14
```

**Trade-off:** Longer CI runtime (3 more test jobs).

---

### Fix 2: Add Windows-Specific Event Loop Policy

**File:** `tests/conftest.py`

```python
import sys
import pytest

@pytest.fixture(scope="session", autouse=True)
def windows_event_loop_policy():
    """Configure Windows event loop policy for async tests."""
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

---

### Fix 3: Ensure Cross-Platform Path Handling

**File:** `shared/utils.py`

Review all `Path` operations:

```python
from pathlib import Path

# ✅ Good: Uses pathlib (cross-platform)
project_root = Path(__file__).parent.parent

# ✅ Good: Forward slashes work on Windows with pathlib
config_path = project_root / "config" / "default.json"

# ❌ Bad: String concatenation with hardcoded separators
config_path = str(project_root) + "/config/default.json"
```

**Current Status:** All path operations in `shared/utils.py` already use `pathlib.Path` ✅

---

### Fix 4: Normalize Line Endings in Git

**File:** `.gitattributes` (create if doesn't exist)

```gitattributes
# Auto-normalize line endings
* text=auto

# Python files always use LF
*.py text eol=lf

# Shell scripts always use LF
*.sh text eol=lf

# PowerShell scripts always use CRLF
*.ps1 text eol=crlf

# YAML files always use LF
*.yml text eol=lf
*.yaml text eol=lf

# JSON files always use LF
*.json text eol=lf

# Markdown files always use LF
*.md text eol=lf
```

---

### Fix 5: Add Timeout to Async Tests

**Rationale:** Windows async tests may hang indefinitely.

```python
# In pytest.ini
[pytest]
addopts =
    -v
    --strict-markers
    --tb=short
    --timeout=60  # Add 60-second timeout per test
```

**Requires:** `pip install pytest-timeout`

---

### Fix 6: Skip Problematic Tests on Windows (Temporary)

**Use case:** If a specific test is Windows-incompatible.

```python
import sys
import pytest

@pytest.mark.skipif(sys.platform == "win32", reason="Fails on Windows - investigating")
def test_problematic_function():
    pass
```

**Note:** Use sparingly - prefer fixing root cause.

---

## Testing the Fixes

### Local Testing (Windows)

```powershell
# Test with Python 3.12
py -3.12 -m pytest tests/ -v --tb=short

# Test with Python 3.13
py -3.13 -m pytest tests/ -v --tb=short

# Test with current version (3.14)
pytest tests/ -v --tb=short
```

### CI Testing

1. Create a branch: `git checkout -b fix/windows-ci`
2. Apply fixes
3. Push: `git push origin fix/windows-ci`
4. Monitor GitHub Actions run
5. Merge when all tests pass

---

## Quick Win: Investigate Annotations

**Immediate Action:**

1. Go to GitHub repository
2. Click "Actions" tab
3. Click the failed workflow run
4. Expand "test (windows-latest, 3.12)" job
5. Look for error messages in the "Run tests with pytest" step
6. Copy error messages to determine root cause

**Expected Information:**
- Specific test that failed
- Error traceback
- Whether it's path-related, async-related, or dependency-related

---

## Cost Impact

**Phase 1:** $0/month (all local/CI is free GitHub Actions)

**CI Runtime Impact:**
- Current: ~6 test jobs (2 versions × 3 OS)
- With Python 3.14: ~9 test jobs (3 versions × 3 OS)
- Free tier: 2,000 minutes/month (plenty of capacity)

---

## Success Criteria

All CI jobs should pass:
- ✅ code-quality
- ✅ validate-structure
- ✅ test (ubuntu-latest, 3.12)
- ✅ test (ubuntu-latest, 3.13)
- ✅ test (macos-latest, 3.12)
- ✅ test (macos-latest, 3.13)
- ✅ test (windows-latest, 3.12) ← **TARGET**
- ✅ test (windows-latest, 3.13) ← **TARGET**
- ✅ docker-build (on main branch push)

---

## Next Steps

### Priority 1: Get Annotations (5 minutes)
1. Review GitHub Actions failure logs
2. Document specific error messages
3. Determine if it's path, async, or dependency issue

### Priority 2: Apply Likely Fix (15 minutes)
1. Add Windows event loop policy to `conftest.py`
2. Create `.gitattributes` for line ending normalization
3. Test locally with Python 3.12/3.13 (if available)

### Priority 3: Push and Monitor (30 minutes)
1. Commit fixes
2. Push to feature branch
3. Monitor CI run
4. Iterate if needed

### Priority 4: Update Documentation (10 minutes)
1. Document the fix in PHASE1-STATUS.md
2. Update SETUP-GUIDE.md with Windows-specific notes
3. Close this troubleshooting ticket

---

## Reference Links

- **GitHub Actions Workflow:** `.github/workflows/dev-ci.yml`
- **Pytest Config:** `pytest.ini`
- **Test Fixtures:** `tests/conftest.py`
- **Shared Utilities:** `shared/utils.py`
- **Project Status:** `PHASE1-STATUS.md`

---

**Last Updated:** 2026-01-19
**Issue Opened:** 2026-01-19
**Status:** 🔍 Diagnosis in progress
