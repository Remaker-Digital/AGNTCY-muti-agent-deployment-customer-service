# AGNTCY Multi-Agent Customer Service Platform - Quick Reference Guide

**Repository**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service
**Project Board**: https://github.com/orgs/Remaker-Digital/projects/1
**Current Phase**: Phase 1 Complete (100%) / Phase 2 Ready to Start
**Last Updated**: 2026-01-22

---

## 🚀 Quick Start

### For New Team Members
1. Read **README.md** - Project overview and setup instructions
2. Read **CLAUDE.md** - Development guidelines and current status
3. Read **PROJECT-README.txt** - Complete requirements and architecture
4. Review **SESSION-SUMMARY-2026-01-22.md** - Recent work completed

### For Developers Starting Phase 2
1. Read **PHASE-2-READINESS.md** - Complete work breakdown and requirements
2. Review **user-stories-phased.md** - User story catalog
3. Check **AGNTCY-REVIEW.md** - SDK integration patterns
4. Review issues **#24-#73** on GitHub - Phase 2 user stories

### For AI Assistants (Claude Code)
1. **CLAUDE.md** - Primary guidance document (MUST READ FIRST)
2. **PROJECT-README.txt** - Requirements and constraints
3. **PHASE-2-READINESS.md** - Current phase context
4. **SESSION-SUMMARY-2026-01-22.md** - Recent session recap

---

## 📁 Documentation Structure

### Primary Documentation (Read These First)

| File | Purpose | Key Content |
|------|---------|-------------|
| **CLAUDE.md** | AI assistant guidance | Development guidelines, phase status, constraints, architecture decisions |
| **PROJECT-README.txt** | Project requirements | Objectives, KPIs, technical constraints, budget, all 5 phases |
| **README.md** | Public-facing docs | Setup instructions, quick start, contribution guidelines |

### Phase Documentation

| File | Purpose | Status |
|------|---------|--------|
| **PHASE-2-READINESS.md** | Phase 2 preparation | ⏳ Current - Awaiting user input |
| **user-stories-phased.md** | Complete user story catalog | ✅ All 130 stories documented |

### Technical Documentation

| File | Purpose | Key Content |
|------|---------|-------------|
| **AGNTCY-REVIEW.md** | SDK integration guide | Factory patterns, A2A protocol, message formats |
| **docker-compose.yml** | Local environment | 13 services: 5 agents + 4 mocks + 4 infrastructure |

### Project Management Documentation

| File | Purpose | Key Content |
|------|---------|-------------|
| **PROJECT-SETUP-COMPLETE.md** | GitHub setup summary | 137 issues created, labels, milestones, scripts |
| **PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md** | PM best practices | GitHub Projects guide, workflows, conventions |
| **SESSION-SUMMARY-2026-01-22.md** | Recent session recap | Work completed, challenges resolved, next steps |
| **github-project-info.json** | Project metadata | Project ID, URL, configuration details |

---

## 🗂️ File Organization by Purpose

### For Understanding the Project
```
1. README.md                    - Start here (public overview)
2. PROJECT-README.txt          - Complete requirements
3. CLAUDE.md                   - Development context
4. AGNTCY-REVIEW.md           - Technical architecture
```

### For Starting Work
```
1. PHASE-2-READINESS.md       - Current phase requirements
2. user-stories-phased.md     - All user stories
3. GitHub Issues #24-#73      - Phase 2 stories
4. docker-compose.yml         - Local environment
```

### For GitHub Project Management
```
1. PROJECT-SETUP-COMPLETE.md  - Setup summary
2. github-project-info.json   - Project metadata
3. *.ps1 scripts              - Automation scripts
4. PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md - Best practices
```

### For Session Continuity
```
1. SESSION-SUMMARY-2026-01-22.md  - Latest session recap
2. CLAUDE.md                      - Current status
3. PROJECT-README.txt             - Updated phase status
4. PHASE-2-READINESS.md           - Next steps
```

---

## 🔧 Automation Scripts

All scripts located in project root:

| Script | Purpose | Output |
|--------|---------|--------|
| **setup-github-cli.ps1** | GitHub CLI setup | Authentication, PATH configuration |
| **create-labels.ps1** | Create all labels | 30 labels across 5 categories |
| **create-epics-and-milestones.ps1** | Create epics & milestones | 7 epics, 5 milestones |
| **create-all-130-stories.ps1** | Create Phase 1 stories | 15 issues (#9-#23) |
| **create-remaining-115-stories.ps1** | Create Phase 2 stories | 50 issues (#24-#73) |
| **create-phases-3-4-5.ps1** | Create Phase 3-5 stories | 65 issues (#74-#138) |

**Total**: 137 issues created with 100% success rate

---

## 📊 GitHub Project Structure

### Issues Overview
- **Total**: 137 issues
- **Epics**: 7 (#2-#8)
- **User Stories**: 130 (#9-#138)
- **Success Rate**: 100% (0 errors)

### By Phase
| Phase | Stories | Issues | Status |
|-------|---------|--------|--------|
| Phase 1 | 15 | #9-#23 | ✅ Complete |
| Phase 2 | 50 | #24-#73 | ⏳ Ready to start |
| Phase 3 | 20 | #74-#93 | Planned |
| Phase 4 | 30 | #94-#123 | Planned |
| Phase 5 | 15 | #124-#138 | Planned |

### By Actor
| Actor | Stories | Epic | Example Stories |
|-------|---------|------|-----------------|
| Customer | 40 | #2 | Order status, product inquiries, returns |
| Prospect | 25 | #3 | Product discovery, email signup |
| Support | 15 | #4 | Ticket management, escalation handling |
| Service | 15 | #5 | Service requests, warranty |
| Sales | 15 | #6 | Lead scoring, bulk orders |
| AI Assistant | 5 | #7 | Proactive engagement |
| Operator | 15 | #8 | Environment setup, monitoring, testing |

---

## 🎯 Current Status

### Phase 1: Infrastructure & Containers
**Status**: ✅ 100% COMPLETE (as of 2026-01-22)

**Completed**:
- Docker Compose with 13 services
- 4 mock APIs (Shopify, Zendesk, Mailchimp, Google Analytics)
- 5 agent skeletons with AGNTCY SDK integration
- Shared utilities (factory, models, utils)
- Test framework (63 tests, 46% coverage)
- GitHub project management (137 issues)

**Remaining**: GitHub Actions CI workflow (deferred to Phase 2)

### Phase 2: Business Logic Implementation
**Status**: ⏳ READY TO START (awaiting user input)

**Required Before Starting**:
1. Response style preference (Concise/Conversational/Detailed)
2. Escalation thresholds
3. Automation goals
4. Test scenarios & customer personas
5. Knowledge base content
6. Story prioritization (top 15 from #24-#73)
7. Development approach (Sequential/Parallel/Story-driven)

**See**: PHASE-2-READINESS.md for complete details

---

## 🔗 Quick Links

### GitHub
- **Project Board**: https://github.com/orgs/Remaker-Digital/projects/1
- **All Issues**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues
- **Milestones**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/milestones
- **Labels**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/labels

### Filtered Views
- **Phase 1 Issues**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues?q=label:phase-1
- **Phase 2 Issues**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues?q=label:phase-2
- **Customer Stories**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues?q=label:actor:customer
- **Critical Priority**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues?q=label:priority:critical

### External Resources
- **Blog Post**: https://www.remakerdigital.com/project/ai-powered-customer-engagement-platform/
- **AGNTCY SDK**: https://github.com/agntcy/app-sdk
- **PyPI Package**: https://pypi.org/project/agntcy-app-sdk/

---

## 💻 Development Environment

### Prerequisites
- **OS**: Windows 11
- **IDE**: Visual Studio Code
- **Containers**: Docker Desktop for Windows
- **Version Control**: GitHub Desktop
- **Python**: 3.12+ (required by AGNTCY SDK)

### Setup Commands
```bash
# Clone repository
git clone https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service.git
cd AGNTCY-muti-agent-deployment-customer-service

# Install Python dependencies
pip install -r requirements.txt

# Start local environment
docker-compose up

# Run tests
pytest tests/

# View logs
docker-compose logs -f

# Stop environment
docker-compose down
```

### Service Endpoints (Local)
- **Mock Shopify API**: http://localhost:8001
- **Mock Zendesk API**: http://localhost:8002
- **Mock Mailchimp API**: http://localhost:8003
- **Mock Google Analytics**: http://localhost:8004
- **Grafana Dashboard**: http://localhost:3001
- **OpenTelemetry Collector**: http://localhost:4318

---

## 📋 Common Tasks

### Starting a New Work Session
1. Read **CLAUDE.md** for current status
2. Review **PHASE-2-READINESS.md** if working on Phase 2
3. Pull latest changes: `git pull`
4. Start environment: `docker-compose up`
5. Run tests to validate: `pytest tests/`

### Creating a New User Story Manually
1. Go to: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues/new
2. Use template from **user-stories-phased.md**
3. Add labels: type, priority, component, phase, actor
4. Assign to milestone
5. Link to parent epic in description

### Running Automation Scripts
```powershell
# Authenticate GitHub CLI (one-time)
.\setup-github-cli.ps1

# Create labels (if needed)
.\create-labels.ps1

# Create additional stories (modify script first)
.\create-all-130-stories.ps1
```

### Updating Phase Status
1. Update **CLAUDE.md** - Phase section and "Recent Updates"
2. Update **PROJECT-README.txt** - PLAN section status
3. Create session summary if significant work completed
4. Update milestone completion % on GitHub

---

## 🎓 Learning Resources

### For Understanding Multi-Agent Systems
- **AGNTCY-REVIEW.md** - SDK integration patterns
- **shared/factory.py** - Factory pattern implementation
- **agents/** - Example agent structures

### For Understanding GitHub Projects
- **PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md** - Complete guide
- **PROJECT-SETUP-COMPLETE.md** - Implementation example

### For Understanding the Business Domain
- **PROJECT-README.txt** - KPIs, objectives, constraints
- **user-stories-phased.md** - All customer scenarios
- Blog post (linked above)

---

## 🚨 Important Notes

### Budget Constraints
- **Phase 1-3**: $0/month (local development only)
- **Phase 4-5**: $200/month maximum (Azure production)
- Cost optimization is a KEY learning objective
- Always consider budget impact before suggesting Azure services

### Development Constraints
- **Python Version**: 3.12+ required by AGNTCY SDK
- **Primary Language**: US English (code, docs, logs)
- **Multi-Language**: Phase 4 only (Canadian French, Spanish)
- **No Real APIs**: Phase 1-3 use mocks only

### Testing Requirements
- **Unit Tests**: >80% coverage target
- **Integration Tests**: Against mock services
- **Current Coverage**: 46% (Phase 1 baseline)
- **Phase 2 Target**: >70% coverage

---

## 📞 Getting Help

### Project Documentation Issues
- Check **CLAUDE.md** first (most comprehensive)
- Review **SESSION-SUMMARY-2026-01-22.md** for recent changes
- Search GitHub issues for similar questions

### Technical Implementation Questions
- Review **AGNTCY-REVIEW.md** for SDK patterns
- Check existing agent implementations in **agents/**
- Review test examples in **tests/**

### Project Management Questions
- See **PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md**
- Review **PROJECT-SETUP-COMPLETE.md** for setup details

---

## ✅ Phase 2 Entry Checklist

Before starting Phase 2 implementation:

**Phase 1 Validation**:
- [ ] All 5 agent skeletons exist in `agents/`
- [ ] All 4 mock APIs respond correctly (test with curl)
- [ ] Docker Compose runs without errors
- [ ] All 63 tests pass: `pytest tests/`
- [ ] Coverage at 46% baseline: `pytest --cov`

**User Input Received**:
- [ ] Response style preference documented
- [ ] Escalation thresholds defined
- [ ] Automation goals specified
- [ ] Test scenarios provided
- [ ] Knowledge base content available
- [ ] Story priorities set (top 15)
- [ ] Development approach chosen

**Environment Ready**:
- [ ] `docker-compose up` successful
- [ ] All services healthy
- [ ] Pytest runs without errors
- [ ] AGNTCY SDK factory initializes

**See PHASE-2-READINESS.md for complete checklist**

---

**This guide provides quick navigation to all project resources.**
**For detailed information, refer to the specific documents linked above.**

---

**Last Updated**: 2026-01-22
**Maintained By**: Project team
**Next Review**: Upon Phase 2 completion
