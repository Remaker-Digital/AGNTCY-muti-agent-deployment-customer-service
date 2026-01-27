# Code Optimization Guide

This guide describes the optimization patterns and tools used in this project to reduce token usage during AI-assisted development while maintaining code quality.

## Overview

The codebase has been optimized to reduce context window usage by **42%** through:
- Shared `BaseAgent` abstract class pattern
- Modular formatter architecture
- Automated optimization checks
- Scheduled maintenance workflow

## BaseAgent Pattern

All 6 agents inherit from `shared/base_agent.py`, which provides:

### Common Functionality (341 lines saved per agent)
- Azure OpenAI client initialization with fallback
- A2A message handling wrapper
- Logging and statistics tracking
- Graceful cleanup with resource management
- Error handling and retry logic

### Usage Pattern
```python
from shared.base_agent import BaseAgent

class IntentClassificationAgent(BaseAgent):
    """Classifies customer intent from messages."""

    def __init__(self):
        super().__init__(
            agent_name="intent-classification-agent",
            agent_topic="intent-classifier"
        )

    async def process_message(self, content: dict, message: dict) -> dict:
        """Agent-specific message processing logic."""
        # Your implementation here
        pass
```

### Benefits
| Metric | Before | After | Impact |
|--------|--------|-------|--------|
| Total Agent Code | 4,844 lines | 2,814 lines | -42% |
| Tokens per Session | ~15,000 | ~10,000 | -33% |
| Maintenance Burden | 6 copies | 1 copy | -83% |

## Formatter Modules

Response generation logic is split into focused modules:

```
agents/response_generation/
├── agent.py                 # Core agent (346 lines)
└── formatters/
    ├── __init__.py          # Package exports
    ├── order.py             # ORDER_STATUS, REFUND_REQUEST, RETURN_REQUEST
    ├── product.py           # PRODUCT_INFO, PRODUCT_RECOMMENDATION, BREWER_SUPPORT
    ├── support.py           # SHIPPING_QUESTION, AUTO_DELIVERY, GIFT_CARD, LOYALTY
    └── escalation.py        # ESCALATION_NEEDED, GENERAL_INQUIRY
```

### Benefits
- Single formatter: ~150-200 lines (vs 1,300 line monolith)
- Faster AI comprehension of targeted code
- Independent testing and modification

## Automated Optimization Check

Run the check script to identify optimization opportunities:

```powershell
.\scripts\check-optimization.ps1
```

### Checks Performed
1. **CLAUDE.md Size** - Alerts when exceeding 900 lines
2. **Agent File Sizes** - Flags agents over 500 lines
3. **Large Python Files** - Lists files over 300 lines
4. **Requirements Consistency** - Identifies duplicate packages
5. **BaseAgent Adoption** - Verifies all agents use shared class

### Sample Output
```
========================================
  OPTIMIZATION STATUS CHECK
========================================

[1/5] Checking CLAUDE.md size...
  [OK] CLAUDE.md: 756 lines (144 lines until archive needed)

[2/5] Checking agent file sizes...
  Total agent code: 2337 lines

[5/5] Checking BaseAgent adoption...
  Agents using BaseAgent: 6 / 6
  [OK] All agents use BaseAgent

========================================
  SUMMARY
========================================
[OK] No optimization issues found!
```

## Maintenance Schedule

| Task | Frequency | Trigger | Script |
|------|-----------|---------|--------|
| Archive CLAUDE.md | Weekly | >900 lines | `archive-claude-history.ps1` |
| Consolidate requirements | Monthly | New packages | Manual review |
| Extract shared patterns | Quarterly | New agents | Code review |
| Split large files | As needed | >500 lines | Manual refactor |

## CLAUDE.md Archiving

When CLAUDE.md grows large, archive historical content:

```powershell
# Preview what will be archived
.\scripts\archive-claude-history.ps1 -DryRun

# Execute archiving
.\scripts\archive-claude-history.ps1
```

Historical content moves to `docs/CLAUDE-HISTORY.md` while keeping active references.

## Test Validation

After any optimization, verify with the test suite:

```powershell
# Run all tests
python -m pytest tests/ -v

# Quick summary
python -m pytest tests/ --tb=no -q
```

### Expected Results
- 116+ tests passing
- 52%+ coverage
- 0 errors (some failures may be pre-existing)

## Directory Structure

```
project/
├── shared/
│   ├── base_agent.py        # Abstract base class (341 lines)
│   ├── azure_openai.py      # Shared OpenAI client
│   ├── models.py            # Data models
│   └── utils.py             # Utilities
├── agents/
│   ├── intent_classification/
│   │   └── agent.py         # 434 lines (was 626)
│   ├── knowledge_retrieval/
│   │   └── agent.py         # 758 lines (was 1,208)
│   ├── response_generation/
│   │   ├── agent.py         # 346 lines (was 1,300)
│   │   └── formatters/      # Modular formatters
│   └── ...
├── scripts/
│   ├── check-optimization.ps1
│   └── archive-claude-history.ps1
└── docs/
    └── OPTIMIZATION-WORKFLOW.md
```

## Key Principles

1. **DRY (Don't Repeat Yourself)** - Common patterns belong in `shared/`
2. **Single Responsibility** - Each formatter handles one intent type
3. **Testability** - Smaller files are easier to test in isolation
4. **Maintainability** - One fix applies to all agents via BaseAgent

## Related Documentation

- [OPTIMIZATION-WORKFLOW.md](./OPTIMIZATION-WORKFLOW.md) - Detailed procedures
- [SESSION-2026-01-27-OPTIMIZATION.md](./SESSION-2026-01-27-OPTIMIZATION.md) - Session details
- [CLAUDE.md](../CLAUDE.md) - Project context and guidance
