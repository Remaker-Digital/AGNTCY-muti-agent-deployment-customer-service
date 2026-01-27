# Documentation Index

**Last Updated:** 2026-01-26
**Project Phase:** Phase 4 Infrastructure Deployed

This directory contains all project documentation. Below is a guide to help you navigate the most important documents.

---

## Quick Start

| If you need to... | Read this document |
|-------------------|-------------------|
| Understand the project | [../CLAUDE.md](../CLAUDE.md) |
| See current architecture | [WIKI-Architecture.md](WIKI-Architecture.md) |
| Check Phase 4 deployment status | [PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md](PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md) |
| Review budget and costs | [BUDGET-SUMMARY.md](BUDGET-SUMMARY.md) |
| Troubleshoot issues | [TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md) |

---

## Core Documentation

### Architecture & Design
| Document | Purpose |
|----------|---------|
| [WIKI-Architecture.md](WIKI-Architecture.md) | Complete system architecture (GitHub Wiki ready) |
| [architecture-requirements-phase2-5.md](architecture-requirements-phase2-5.md) | Architectural specifications for Phases 2-5 |
| [critic-supervisor-agent-requirements.md](critic-supervisor-agent-requirements.md) | Content validation agent specification |
| [execution-tracing-observability-requirements.md](execution-tracing-observability-requirements.md) | OpenTelemetry instrumentation requirements |
| [data-staleness-requirements.md](data-staleness-requirements.md) | Data consistency requirements per agent |
| [event-driven-requirements.md](event-driven-requirements.md) | Event-driven architecture specification |

### Operational Guides
| Document | Purpose |
|----------|---------|
| [PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md](PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md) | Azure deployment reference and remaining work |
| [TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md) | Common issues and solutions |
| [CONSOLE-DOCUMENTATION.md](CONSOLE-DOCUMENTATION.md) | Development console user guide |
| [BUDGET-SUMMARY.md](BUDGET-SUMMARY.md) | Cost tracking and budget management |

### UCP Integration (Phase 4-5)
| Document | Purpose |
|----------|---------|
| [EVALUATION-Universal-Commerce-Protocol-UCP.md](EVALUATION-Universal-Commerce-Protocol-UCP.md) | UCP strategic evaluation |
| [UCP-IMPLEMENTATION-COMPLEXITY-ANALYSIS.md](UCP-IMPLEMENTATION-COMPLEXITY-ANALYSIS.md) | Effort estimates for UCP |
| [MCP-TESTING-VALIDATION-APPROACH.md](MCP-TESTING-VALIDATION-APPROACH.md) | Testing strategy for MCP/UCP |
| [WIKI-UCP-Integration-Guide.md](WIKI-UCP-Integration-Guide.md) | UCP integration wiki page |
| [COMPARISON-Shopify-Shop-Chat-Agent.md](COMPARISON-Shopify-Shop-Chat-Agent.md) | Architecture comparison |

### Status & Summaries
| Document | Purpose |
|----------|---------|
| [PHASE-3-COMPLETION-SUMMARY.md](PHASE-3-COMPLETION-SUMMARY.md) | Phase 3 testing results |
| [PHASE-2-COMPLETION-ASSESSMENT.md](PHASE-2-COMPLETION-ASSESSMENT.md) | Phase 2 business logic completion |
| [E2E-BASELINE-RESULTS-2026-01-24.md](E2E-BASELINE-RESULTS-2026-01-24.md) | End-to-end test baseline |

---

## Archived Documentation

Historical documents (daily logs, session summaries, etc.) have been moved to `docs/archive/` to reduce clutter. These remain available for reference but are no longer actively maintained.

| Archive Contents | Count |
|-----------------|-------|
| Phase 3 Daily Summaries | 11 files |
| Session Summaries | 3 files |
| Phase 3 Progress/Kickoff | 2 files |

---

## Evaluation Results

AI model evaluation results from Phase 3.5 are in `../evaluation/`:

| Path | Contents |
|------|----------|
| `evaluation/prompts/` | 5 production-ready prompts |
| `evaluation/datasets/` | 7 evaluation datasets (375 samples) |
| `evaluation/results/` | 6 evaluation reports + completion summary |

---

## External Links

- **GitHub Project Board:** [View Board](https://github.com/orgs/Remaker-Digital/projects/1)
- **Repository:** [GitHub](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service)
- **AGNTCY SDK Docs:** [docs.agntcy.com](https://docs.agntcy.com)

---

## Document Maintenance

When updating documentation:

1. **Keep current:** Update "Last Updated" dates when making changes
2. **Archive old content:** Move superseded daily logs to `archive/`
3. **Update this README:** Add new documents to the appropriate section
4. **Maintain CLAUDE.md:** Keep the main project guidance current

---

**Maintained by:** Claude Code Assistant
