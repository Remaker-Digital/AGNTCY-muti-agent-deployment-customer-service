# Optimization Workflow

This document defines repeatable optimization operations for reducing token usage and improving maintainability. These operations are designed to be safe, reversible, and preserve functionality.

## Quick Reference

| Operation | Risk | Frequency | Automated Check |
|-----------|------|-----------|-----------------|
| Archive historical docs | Very Low | Weekly | Line count check |
| Consolidate requirements | Low | Monthly | pip install test |
| Extract shared patterns | Medium | Quarterly | Unit tests |
| Split large files | Medium | As needed | Import tests |
| Update Dockerfiles | Low | After requirements change | Docker build |

---

## Operation 1: Archive Historical Documentation

**Risk Level:** Very Low
**Frequency:** Weekly or when CLAUDE.md exceeds 900 lines
**Time:** 5-10 minutes

### Trigger Conditions
- CLAUDE.md exceeds 900 lines
- Session summaries older than 2 weeks
- Completed phase documentation

### Procedure

1. **Check current size:**
   ```powershell
   (Get-Content CLAUDE.md | Measure-Object -Line).Lines
   ```

2. **Identify archivable content:**
   - Session summaries older than 14 days
   - Completed phase details (keep summary, archive details)
   - Historical update logs

3. **Move to archive:**
   - Append to `docs/CLAUDE-HISTORY.md`
   - Keep header reference in CLAUDE.md
   - Preserve any active/incomplete items

4. **Verify:**
   - Confirm CLAUDE.md still loads correctly
   - Check cross-references aren't broken

### Safety Checks
- [ ] Archive file exists and is readable
- [ ] No active TODO items moved
- [ ] No incomplete phase details moved
- [ ] CLAUDE.md still under 900 lines

### Rollback
```powershell
# Content is preserved in CLAUDE-HISTORY.md - copy back if needed
```

---

## Operation 2: Consolidate Shared Dependencies

**Risk Level:** Low
**Frequency:** Monthly or after adding new packages
**Time:** 15-20 minutes

### Trigger Conditions
- New package added to multiple agents
- Package version inconsistency detected
- Monthly maintenance window

### Procedure

1. **Audit current requirements:**
   ```powershell
   # List all agent requirements
   Get-ChildItem -Path agents -Recurse -Filter "requirements.txt" | ForEach-Object {
       Write-Host "`n=== $($_.FullName) ==="
       Get-Content $_.FullName
   }
   ```

2. **Identify shared packages:**
   - Packages in 3+ agents → move to `requirements-agents.txt`
   - Agent-specific packages → keep in agent's `requirements.txt`

3. **Update `requirements-agents.txt`:**
   ```
   # Core packages used by all agents
   agntcy-app-sdk>=0.2.0
   python-dotenv>=1.0.0
   openai>=1.12.0
   azure-identity>=1.15.0
   httpx>=0.27.0
   ```

4. **Simplify agent requirements:**
   ```
   # Agent-specific dependencies only
   # Shared dependencies in requirements-agents.txt
   # (empty or agent-specific packages only)
   ```

5. **Test installation:**
   ```powershell
   pip install -r requirements-agents.txt
   pip install -r agents/intent_classification/requirements.txt
   ```

### Safety Checks
- [ ] All packages install without errors
- [ ] Version constraints are consistent
- [ ] No circular dependencies
- [ ] Docker builds succeed

### Rollback
```powershell
git checkout requirements-agents.txt agents/*/requirements.txt
```

---

## Operation 3: Extract Shared Patterns to Base Classes

**Risk Level:** Medium
**Frequency:** Quarterly or when adding new agents
**Time:** 2-4 hours

### Trigger Conditions
- New agent added with similar boilerplate
- Pattern duplicated in 3+ agents
- Quarterly code review

### Procedure

1. **Identify duplication:**
   ```powershell
   # Compare agent structures
   Get-ChildItem -Path agents -Recurse -Filter "agent.py" | ForEach-Object {
       Write-Host "`n=== $($_.FullName) ==="
       (Get-Content $_.FullName | Measure-Object -Line).Lines
   }
   ```

2. **Common patterns to extract:**
   - `__init__` boilerplate (config, logging, factory)
   - `initialize()` method (transport, client, OpenAI)
   - `cleanup()` method (stats, shutdown)
   - `run()` and `run_demo_mode()` methods
   - Message handling wrapper

3. **Create/update base class:**
   - Add to `shared/base_agent.py`
   - Use abstract methods for agent-specific logic
   - Preserve all configuration options

4. **Refactor agents one at a time:**
   ```python
   # Before
   class MyAgent:
       def __init__(self):
           self.config = load_config()
           self.logger = setup_logging(...)
           # ... 50 lines of boilerplate

   # After
   class MyAgent(BaseAgent):
       agent_name = "my-agent"
       default_topic = "my-topic"

       async def process_message(self, content, message):
           # Agent-specific logic only
   ```

5. **Test each agent after refactoring:**
   ```powershell
   python -c "from agents.intent_classification.agent import IntentClassificationAgent; print('OK')"
   ```

### Safety Checks
- [ ] All unit tests pass
- [ ] Agent imports work
- [ ] Demo mode runs successfully
- [ ] Docker containers start
- [ ] No functionality removed

### Rollback
```powershell
git checkout shared/base_agent.py agents/*/agent.py
```

---

## Operation 4: Split Large Files into Modules

**Risk Level:** Medium
**Frequency:** When file exceeds 500 lines
**Time:** 1-2 hours per file

### Trigger Conditions
- File exceeds 500 lines
- File has 3+ distinct logical sections
- Multiple contributors editing same file

### Procedure

1. **Identify split candidates:**
   ```powershell
   Get-ChildItem -Path . -Recurse -Include "*.py" | Where-Object {
       (Get-Content $_.FullName | Measure-Object -Line).Lines -gt 500
   } | ForEach-Object {
       Write-Host "$($_.FullName): $((Get-Content $_.FullName | Measure-Object -Line).Lines) lines"
   }
   ```

2. **Identify logical sections:**
   - Group related functions/methods
   - Look for `# ====` section headers
   - Identify standalone utilities

3. **Create module structure:**
   ```
   agents/response_generation/
   ├── agent.py           # Main agent (slim)
   ├── formatters/
   │   ├── __init__.py    # Exports all formatters
   │   ├── order.py       # Order-related formatters
   │   ├── product.py     # Product-related formatters
   │   └── support.py     # Support-related formatters
   ```

4. **Move code to modules:**
   - Keep imports minimal
   - Preserve all docstrings
   - Maintain function signatures

5. **Update main file:**
   ```python
   from agents.response_generation.formatters import (
       format_order_status,
       format_product_info,
       # ...
   )
   ```

6. **Test imports:**
   ```powershell
   python -c "from agents.response_generation.agent import ResponseGenerationAgent; print('OK')"
   ```

### Safety Checks
- [ ] All imports resolve
- [ ] No circular imports
- [ ] All functions accessible
- [ ] Unit tests pass
- [ ] Docstrings preserved

### Rollback
```powershell
git checkout agents/response_generation/
```

---

## Operation 5: Optimize Dockerfiles for Layer Caching

**Risk Level:** Low
**Frequency:** After requirements changes
**Time:** 30 minutes

### Trigger Conditions
- `requirements-agents.txt` updated
- Agent-specific requirements changed
- Docker build times increasing

### Procedure

1. **Update Dockerfile pattern:**
   ```dockerfile
   # Stage 1: Builder
   FROM python:3.12-slim AS builder
   WORKDIR /build

   # Install SHARED requirements first (cached layer)
   COPY requirements-agents.txt .
   RUN pip install --user -r requirements-agents.txt

   # Install agent-specific requirements
   COPY agents/{agent}/requirements.txt agent-requirements.txt
   RUN pip install --user -r agent-requirements.txt 2>/dev/null || true

   # Stage 2: Runtime
   FROM python:3.12-slim
   COPY --from=builder /root/.local /home/appuser/.local
   COPY shared/ /app/shared/
   COPY agents/{agent}/agent.py .
   ```

2. **Test build:**
   ```powershell
   docker build -f agents/intent_classification/Dockerfile -t test-agent .
   ```

3. **Verify layer caching:**
   ```powershell
   # Second build should use cached layers
   docker build -f agents/intent_classification/Dockerfile -t test-agent .
   # Look for "CACHED" in output
   ```

### Safety Checks
- [ ] Docker build succeeds
- [ ] Container starts correctly
- [ ] Health check passes
- [ ] Shared requirements cached

### Rollback
```powershell
git checkout agents/*/Dockerfile
```

---

## Scheduled Maintenance Calendar

### Weekly (Every Monday)
- [ ] Check CLAUDE.md line count
- [ ] Archive historical content if needed
- [ ] Review any new code duplication

### Monthly (First Monday)
- [ ] Audit requirements files
- [ ] Consolidate shared packages
- [ ] Update Docker base images if needed
- [ ] Run full test suite

### Quarterly (First week of quarter)
- [ ] Review agent code for shared patterns
- [ ] Extract new base class methods if needed
- [ ] Split any files exceeding 500 lines
- [ ] Update this workflow document

---

## Metrics to Track

### Token Usage Indicators
| Metric | Target | Check Command |
|--------|--------|---------------|
| CLAUDE.md lines | <900 | `(Get-Content CLAUDE.md \| Measure-Object -Line).Lines` |
| Largest agent file | <500 lines | See Operation 4 |
| Duplicate code blocks | <3 occurrences | Manual review |

### Build Performance
| Metric | Target | Check Command |
|--------|--------|---------------|
| Docker build (cached) | <30 seconds | `Measure-Command { docker build ... }` |
| pip install | <60 seconds | `Measure-Command { pip install -r ... }` |

### Code Quality
| Metric | Target | Check Command |
|--------|--------|---------------|
| Test pass rate | 100% | `pytest --tb=short` |
| Import errors | 0 | `python -c "from agents.* import *"` |

---

## Pre-Optimization Checklist

Before performing any optimization:

1. **Backup current state:**
   ```powershell
   git stash push -m "Pre-optimization backup $(Get-Date -Format 'yyyy-MM-dd')"
   ```

2. **Run tests:**
   ```powershell
   pytest tests/ -v --tb=short
   ```

3. **Document current metrics:**
   - File line counts
   - Test pass rate
   - Docker build time

4. **Verify git status is clean:**
   ```powershell
   git status
   ```

---

## Post-Optimization Checklist

After completing any optimization:

1. **Run full test suite:**
   ```powershell
   pytest tests/ -v
   ```

2. **Test Docker builds:**
   ```powershell
   docker-compose build
   ```

3. **Verify imports:**
   ```powershell
   python -c "from shared import *; from agents.intent_classification.agent import *; print('OK')"
   ```

4. **Update metrics:**
   - Record new line counts
   - Note any performance changes

5. **Commit with descriptive message:**
   ```powershell
   git add -A
   git commit -m "Optimization: [description]

   - Files affected: [list]
   - Lines reduced: [count]
   - Tests: All passing"
   ```

---

## Optimization History

### 2026-01-27: Validation & Bug Fixes
- Fixed `check-optimization.ps1` to exclude `venv/` and `node_modules/` directories
- Restored `_analyze_mock()` method in EscalationAgent for test backward compatibility
- Fixed async cleanup error ("no running event loop") in EscalationAgent.cleanup()

**Test Results After Optimization:**
| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Passed | ~116 | 116 | ✅ Stable |
| Failed | ~15 | 15 | ✅ Stable (pre-existing) |
| Errors | 6 | 0 | ✅ Fixed |
| Coverage | ~52% | 52% | ✅ Stable |

**Current Codebase Metrics:**
- CLAUDE.md: 756 lines (144 until threshold)
- Total agent code: 2,337 lines
- BaseAgent adoption: 6/6 agents (100%)

### 2026-01-26: Initial Optimization Suite
- Created `shared/base_agent.py` (341 lines)
- Refactored 6 agents to use BaseAgent
- Created `requirements-agents.txt`
- Split response_generation into formatters module
- Created `mocks/shared/__init__.py`
- Reduced CLAUDE.md by 183 lines

**Agent Refactoring Results:**
| Agent | Before | After | Reduction |
|-------|--------|-------|-----------|
| Intent Classification | 626 | 434 | 31% |
| Escalation | 633 | 517 | 18% |
| Analytics | 322 | 266 | 17% |
| Knowledge Retrieval | 1,208 | 758 | 37% |
| Critic/Supervisor | 755 | 493 | 35% |
| Response Generation | 1,300 | 346 | 73% |
| **Total** | **4,844** | **2,814** | **42%** |

**Estimated Token Savings:**
- Per-session reduction: ~3,600-4,800 tokens (from shared BaseAgent pattern)
- Response formatter modules: ~900 tokens/read (split from single 1,300-line file)

---

## Automated Check Script

Run `scripts/check-optimization.ps1` to check current status:

```powershell
.\scripts\check-optimization.ps1
```

**Output includes:**
1. CLAUDE.md line count vs threshold (900 lines)
2. Agent file sizes (threshold: 500 lines)
3. Large Python files (threshold: 300 lines)
4. Requirements consistency check
5. BaseAgent adoption status

**Exit Codes:**
- `0` = No issues found
- `1` = Issues requiring attention

---

## Contact

For questions about this workflow, see CLAUDE.md or create a GitHub issue.
