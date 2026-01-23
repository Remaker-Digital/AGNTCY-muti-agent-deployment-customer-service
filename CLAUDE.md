# CLAUDE.md - AI Assistant Guidance for This Project

This document provides context and guidance for AI assistants (Claude, GitHub Copilot, etc.) working on this multi-agent customer service platform project.

## Project Overview

**Type:** Educational example project for public GitHub repository and blog post series
**Purpose:** Demonstrate building a cost-effective multi-agent AI system on Azure using AGNTCY SDK
**License:** Public (educational use)
**Audience:** Developers learning multi-agent architectures, Azure deployment, and cost optimization

## Critical Context

### Budget Constraints (HIGHEST PRIORITY)
- **Phase 1-3:** $0/month (local development only, no cloud resources)
- **Phase 4-5:** $265-300/month maximum (Azure production deployment - **REVISED 2026-01-22**)
  - Original budget: $200/month
  - Revised to accommodate new architectural requirements (PII tokenization, event-driven, RAG)
  - Post Phase 5 cost optimization target: $180-220/month
- **Cost optimization is a KEY LEARNING OBJECTIVE** - always suggest cost-effective solutions
- Recommend serverless, pay-per-use, and Basic/Standard tiers over Premium services
- Question any suggestion that would exceed revised budget constraints

### Development Environment
- **OS:** Windows 11
- **IDE:** Visual Studio Code
- **Container Platform:** Docker Desktop for Windows
- **Version Control:** GitHub Desktop + GitHub repository (public)
- **Python Version:** 3.12+ (required by AGNTCY SDK)
- **Primary Language:** US English (code, docs, comments, logs)

### Technology Stack (Non-Negotiable)
- **Multi-Agent Framework:** AGNTCY SDK (installed via PyPI: `pip install agntcy-app-sdk`)
- **Infrastructure-as-Code:** Terraform (for Azure resources)
- **CI/CD:** GitHub Actions (Phase 1-3), Azure DevOps Pipelines (Phase 4-5)
- **Containerization:** Docker + Docker Compose
- **Cloud Platform:** Microsoft Azure (East US region)

## Project Phases

### Phase 1: Infrastructure & Containers ($0 budget) - **100% COMPLETE** ✅
**Status as of 2026-01-22:**
- ✅ Docker Compose with 13 services running
- ✅ All 4 mock APIs implemented (Shopify, Zendesk, Mailchimp, Google Analytics)
- ✅ All 5 agents implemented with AGNTCY SDK integration
- ✅ Shared utilities complete (factory, models, utils)
- ✅ Test framework complete (63 tests passing, 46% coverage)
- ✅ GitHub Project Management setup complete (137 issues)
- ⏳ GitHub Actions CI workflow (remaining - deferred to Phase 2)

**Completed Implementation:**
- Mock APIs: 4/4 complete with test fixtures
- Agents: 5/5 complete with A2A/MCP protocols
- Tests: 100% coverage on shared utilities, 46% overall
- Documentation: All .md files updated
- GitHub Projects: 7 epics, 130 user stories, 30 labels, 5 milestones

**When working on Phase 1:**
- Phase 1 is now 100% complete
- All external services are mocked (no API calls)
- All agents have demo mode for testing without full SDK
- Test coverage: 46% is baseline for Phase 1 (mock implementations)

### Phase 2: Business Logic Implementation ($0 budget) - **READY TO START** ⏳
**Status as of 2026-01-22:**
- 📋 50 user stories created (Issues #24-#73)
- 📋 PHASE-2-READINESS.md prepared with complete work breakdown
- ⏳ Awaiting user input on business logic decisions
- ⏳ Ready to begin implementation once inputs received

**Focus:** Agent implementations with AGNTCY SDK patterns
- Implement 5 core agents: Intent Classification, Knowledge Retrieval, Response Generation, Escalation, Analytics
- Use A2A protocol for agent-to-agent communication
- Integration tests against mock services
- Session management and conversation state handling
- Still fully local, no cloud resources

**Required Before Starting Phase 2:**
1. Response style & tone preference (Concise/Conversational/Detailed)
2. Escalation thresholds (when to escalate to humans)
3. Automation goals (which queries to automate)
4. Test scenarios & customer personas
5. Knowledge base content (policies, shipping info)
6. Story prioritization (rank top 15 stories)
7. Development approach (Sequential/Parallel/Story-driven)

**See PHASE-2-READINESS.md for complete details**

**When working on Phase 2:**
- Use AGNTCY factory patterns (singleton recommended)
- Implement topic-based routing between agents
- Use Message format with contextId/taskId for conversation threading
- All AI/LLM responses should be canned/mocked (no real API calls)
- Test multi-agent conversation flows end-to-end
- Target: Increase test coverage from 46% to >70%

**New Architectural Requirements (Added 2026-01-22):**
1. **PII Tokenization:** Design and mock tokenization service for third-party AI services
2. **Data Abstraction Layer:** Design multi-store interfaces (Cosmos, Blob, Redis, mock)
3. **Event-Driven Architecture:** Design event ingestion service and NATS schemas
4. **RAG Pipeline:** Design vector embeddings with local FAISS mock

**See docs/architecture-requirements-phase2-5.md for complete specifications**

### Phase 3: Testing & Validation ($0 budget)
**Focus:** Functional testing and performance benchmarking
- End-to-end conversation flow testing
- Load testing with Locust (local hardware limits)
- Performance benchmarks for KPI validation
- GitHub Actions nightly regression suite
- Documentation: testing guides, troubleshooting

**When working on Phase 3:**
- Create realistic customer conversation test scenarios
- Validate all KPIs can be met in local environment
- Performance targets: <2min response time, >70% automation rate
- No cloud services - all testing local

**New Architectural Requirements (Added 2026-01-22):**
1. **PII Tokenization:** Test tokenization with mock third-party AI calls
2. **Multi-Store Access:** Validate staleness tolerances with Docker containers
3. **Event-Driven:** Mock RabbitMQ for webhook and cron testing
4. **RAG:** Validate vector search accuracy with 75-document test knowledge base

### Phase 4: Azure Production Setup ($265-300/month budget - **REVISED 2026-01-22**)
**Focus:** Terraform infrastructure, multi-language support, real API integration, new architectural components
- Deploy to Azure East US region
- Add Canadian French and Spanish language support
- Integrate real Shopify, Zendesk, Mailchimp APIs
- Azure DevOps Pipelines CI/CD
- **NEW:** Deploy Azure Key Vault, NATS JetStream, Cosmos DB vector search, Azure OpenAI

**When working on Phase 4:**
- ALWAYS check cost implications before suggesting Azure services
- Prefer: Container Instances over App Service, Cosmos Serverless over provisioned, Basic tiers
- Avoid: Azure Front Door, Traffic Manager, Premium tiers, geo-replication (unless absolutely necessary)
- Use Terraform for ALL Azure resources
- Implement aggressive auto-scaling (down to 1 instance during idle)
- 7-day log retention (not 30-day default)

**New Architectural Components (Added 2026-01-22):**
1. **PII Tokenization:** Azure Key Vault for token storage, fallback to Cosmos if latency >100ms
2. **Multi-Store:** Cosmos DB Serverless (real-time + vector), Blob Storage + CDN (knowledge base)
3. **Event-Driven:** NATS JetStream, Azure Functions (webhook ingestion), Shopify/Zendesk webhooks
4. **RAG:** Azure OpenAI embeddings (text-embedding-3-large), Cosmos DB vector search (MongoDB API)
5. **5 New User Stories:** Issues #139-#143 (event-driven features)

### Phase 5: Production Deployment & Testing ($265-300/month budget - **REVISED 2026-01-22**)
**Focus:** Production deployment, load testing, security validation, DR drills, new architecture validation
- Deploy to Azure and validate in production
- Load testing: 100 concurrent users, 1000 req/min
- Security scanning (OWASP ZAP, Dependabot, Snyk)
- Disaster recovery validation (quarterly full drill)
- Final blog post and documentation
- **NEW:** Validate PII tokenization, event processing, RAG accuracy

**When working on Phase 5:**
- Monitor Azure costs continuously
- Validate budget alerts are firing correctly at 83% ($250) and 93% ($280) - **REVISED**
- Document all cost optimization decisions for blog readers
- Ensure DR procedures are tested and documented

**New Validation Requirements (Added 2026-01-22):**
1. **PII Tokenization:** Latency <100ms (P95), no data leaks in third-party AI logs
2. **Data Staleness:** Intent <10s, Knowledge <1hr, Response real-time, Escalation <30s, Analytics <15min
3. **Event Processing:** 100 events/sec sustained, <1% error rate, DLQ monitoring
4. **RAG:** Query latency <500ms, retrieval accuracy >90%, 75-document knowledge base

## Key Architecture Decisions

### PII Tokenization & Data Security (Added 2026-01-22)
- **Scope:** PII tokenization ONLY required for third-party AI services (OpenAI API, Anthropic API, etc.)
- **Exempt from tokenization:** Azure OpenAI Service, Microsoft Foundry models (including Anthropic Claude via Azure)
  - Rationale: These services are within the secure Azure perimeter and do not retain customer data
- **Method:** Random UUID tokens (e.g., `TOKEN_a7f3c9e1-4b2d-8f6a-9c3e`)
- **Storage:** Azure Key Vault (Phase 4-5), fallback to Cosmos DB if latency >100ms
- **Fields:** All PII (names, emails, phones, addresses, order IDs, payment info, conversation content)
- **See:** `docs/architecture-requirements-phase2-5.md` Section 1 for complete specification

### Data Abstraction & Multi-Store Strategy (Added 2026-01-22)
- **Real-time (ACID):** Cosmos DB Core for Response Generation Agent (order status, inventory, payments)
- **Near-real-time cache:** Redis (optional, Phase 5 optimization) for Intent/Escalation agents
- **Eventually consistent:** Cosmos DB analytical store for Analytics Agent
- **Static content:** Blob Storage + CDN for Knowledge Retrieval Agent (1hr cache TTL)
- **Staleness tolerances:** Intent 5-10s, Knowledge 1hr, Response real-time, Escalation 30s, Analytics 5-15min
- **See:** `docs/data-staleness-requirements.md` for complete store mapping

### Event-Driven Architecture (Added 2026-01-22)
- **Event Bus:** NATS JetStream (reuses AGNTCY transport layer, $0 incremental cost)
- **Event Sources:** 12 types (Shopify webhooks, Zendesk webhooks, scheduled triggers, RSS)
- **Throttling:** 100 events/sec global, 20/sec per agent, 5 concurrent handlers per agent
- **Retention:** 7 days with replay capability
- **New Stories:** 5 additional user stories (Issues #139-#143 for event-driven features)
- **See:** `docs/event-driven-requirements.md` for complete event catalog and routing

### RAG & Differentiated Models (Added 2026-01-22)
- **Vector Store:** Cosmos DB for MongoDB (vector search, preview feature), ~$5-10/month
- **Embeddings:** Azure OpenAI text-embedding-3-large (1536 dimensions)
- **Knowledge Base:** 75 documents (50 products, 20 articles, 5 policies), ~20K tokens
- **Models by Agent:**
  - Intent Classification: GPT-4o-mini (~$0.15/1M tokens)
  - Response Generation: GPT-4o (~$2.50/1M tokens)
  - Knowledge Retrieval: text-embedding-3-large (~$0.13/1M tokens)
- **Post Phase 5:** Fine-tuned models, self-hosted Qdrant, medium e-commerce scale
- **See:** `docs/architecture-requirements-phase2-5.md` Section 4 for RAG pipeline

### AGNTCY SDK Usage
- **Factory Pattern:** Single `AgntcyFactory` instance per application (singleton)
- **Protocol Choice:**
  - A2A for custom agent logic (Intent, Response, Escalation, Analytics)
  - MCP for external tool integrations (Shopify, Zendesk, Mailchimp)
- **Transport Choice:**
  - SLIM for secure, low-latency agent communication (recommended)
  - NATS for high-throughput scenarios AND event bus (consolidated)
- **Message Format:** Use contextId for conversation threads, taskId for tracking
- **Session Management:** `AppSession` with configurable max_sessions

### Multi-Language Strategy (Phase 4 only)
- **Primary:** US English (all phases)
- **Additional:** Canadian French (fr-CA), Spanish (es) in Phase 4
- **Implementation:** Separate response generation agents per language
- **Routing:** Topic-based (response-generator-en, response-generator-fr-ca, response-generator-es)
- **Translation:** Pre-translated templates (NO real-time translation APIs - cost prohibitive)
- **Detection:** Language metadata field in Intent Classification Agent

### Testing Strategy
- **Phase 1:** Unit tests with mocks, pytest, >80% coverage
- **Phase 2:** Integration tests against mock Docker services
- **Phase 3:** E2E functional tests, Locust load testing (local)
- **Phase 4:** Real API integration tests in Azure staging environment
- **Phase 5:** Production smoke tests, Azure Load Testing, security scans

### Cost Optimization Principles (Phase 4-5)
1. Use pay-per-use over provisioned capacity (Container Instances, Cosmos Serverless)
2. Use Basic/Standard tiers, not Premium (Redis, Container Registry, App Gateway)
3. Auto-scale aggressively DOWN (1 instance minimum per agent)
4. Implement auto-shutdown during low-traffic hours (2am-6am ET)
5. Reduce log retention to 7 days
6. Single region deployment (no geo-replication, no Front Door)
7. Weekly cost reviews and optimization iterations
8. Tag all resources for cost allocation tracking

## Common Pitfalls to Avoid

### ❌ DON'T:
- Suggest Azure services in Phase 1-3 (local development only)
- Recommend Premium tier services without strong justification and budget check
- Use real API keys or cloud resources during Phase 1-3
- Implement real-time translation (use static templates)
- Provision Cosmos DB with RU/s (use Serverless mode)
- Set up geo-replication or multi-region (budget constraint)
- Use default 30-day log retention (use 7 days)
- Suggest services that would exceed $265-300/month budget (revised 2026-01-22)
- Commit secrets to Git (.env files must be in .gitignore)
- Use Python < 3.12 (AGNTCY SDK requirement)

### ✅ DO:
- Always consider cost implications for Phase 4-5 suggestions
- Use mock/stub services for Phase 1-3 development
- Follow AGNTCY SDK factory and message patterns
- Implement comprehensive error handling and logging
- Create realistic test data and scenarios
- Document cost optimization decisions
- Use environment variables for configuration (.env files)
- Tag Docker images with version + commit SHA
- Implement graceful shutdown handlers (SIGTERM/SIGINT)
- Write clear, educational code comments (blog audience)
- Follow Azure best practices for security (Key Vault, Managed Identity, TLS 1.3)

## Third-Party Service Accounts Required

### Phase 1-3: None
All services are mocked locally. No API keys needed.

### Phase 4-5: Required
- **Azure:** Subscription (~$265-300/month - **REVISED**), DevOps organization (free), Service Principal
- **Shopify:** Partner account (free), Development Store (free)
- **Zendesk:** Trial/Sandbox account ($0-49/month) - monitor budget impact
- **Mailchimp:** Free tier account (up to 500 contacts, $0)
- **Google Analytics:** GA4 property (free), Service Account (free)
- **AI Models:** Azure OpenAI Service (~$26/month estimated token usage)
  - GPT-4o-mini for intent classification
  - GPT-4o for response generation
  - text-embedding-3-large for RAG embeddings
  - **Alternative:** Microsoft Foundry (Anthropic Claude via Azure) - also within secure perimeter

**Budget Impact:** Revised total budget $265-300/month accommodates new architectural requirements (PII tokenization, event-driven, RAG, multi-store).

## GitHub Project Management

**Project Board**: https://github.com/orgs/Remaker-Digital/projects/1
**Repository**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service

### Structure (as of 2026-01-22)
- **Epics**: 7 issues (#2-#8) - Actor-based organization
  - Customer Epic (#2) - 40 stories
  - Prospect Epic (#3) - 25 stories
  - Support Epic (#4) - 15 stories
  - Service Epic (#5) - 15 stories
  - Sales Epic (#6) - 15 stories
  - AI Assistant Epic (#7) - 5 stories
  - Operator Epic (#8) - 15 stories

- **User Stories**: 130 issues (#9-#138) organized by phase
  - Phase 1: 15 stories (#9-#23) ✅ Complete
  - Phase 2: 50 stories (#24-#73) ⏳ Ready to start
  - Phase 3: 20 stories (#74-#93) - Testing
  - Phase 4: 30 stories (#94-#123) - Production deployment
  - Phase 5: 15 stories (#124-#138) - Go-live

- **Labels**: 30 total across 5 categories
  - Type: epic, feature, bug, enhancement, test, documentation
  - Priority: critical, high, medium, low
  - Component: infrastructure, agent, api, observability, testing, ci-cd, security, shared
  - Phase: phase-1, phase-2, phase-3, phase-4, phase-5
  - Actor: customer, prospect, support, service, sales, ai-assistant, operator

- **Milestones**: 5 phase-based milestones with due dates
  - Phase 1 - Infrastructure (2026-02-28) ✅ Complete
  - Phase 2 - Business Logic (2026-04-30) ⏳ In progress
  - Phase 3 - Testing (2026-06-30)
  - Phase 4 - Production Deployment (2026-08-31)
  - Phase 5 - Go-Live (2026-09-30)

### Automation Scripts Created
Located in project root:
- `setup-github-cli.ps1` - GitHub CLI setup and authentication
- `create-labels.ps1` - Create all 30 project labels
- `create-epics-and-milestones.ps1` - Create 7 epics and 5 milestones
- `create-all-130-stories.ps1` - Create Phase 1 stories (15 issues)
- `create-remaining-115-stories.ps1` - Create Phase 2 stories (50 issues)
- `create-phases-3-4-5.ps1` - Create Phases 3-5 stories (65 issues)

**Total Success Rate**: 137/137 issues created (100%, 0 errors)

**See PROJECT-SETUP-COMPLETE.md for complete details**

## File Structure Guidelines

```
project-root/
├── agents/                      # Agent implementations
│   ├── intent_classification/   # Each agent has own directory
│   ├── knowledge_retrieval/
│   ├── response_generation/
│   ├── escalation/
│   └── analytics/
├── mocks/                       # Mock API implementations (Phase 1-3)
│   ├── shopify/
│   ├── zendesk/
│   ├── mailchimp/
│   └── google_analytics/
├── shared/                      # Shared utilities
│   ├── factory.py              # AGNTCY factory singleton
│   ├── models.py               # Common message models
│   └── utils.py
├── tests/                       # Test suites
│   ├── unit/                   # Phase 1
│   ├── integration/            # Phase 2
│   └── e2e/                    # Phase 3
├── test-data/                   # Test fixtures (JSON)
│   ├── shopify/
│   ├── zendesk/
│   ├── mailchimp/
│   └── conversations/
├── terraform/                   # Infrastructure-as-Code
│   ├── phase1_dev/             # Local Docker equivalents
│   └── phase4_prod/            # Azure production
├── .github/
│   └── workflows/
│       └── dev-ci.yml          # GitHub Actions (Phase 1-3)
├── docs/                        # Documentation
│   └── dr-test-results/        # Disaster recovery test logs
├── docker-compose.yml           # Local development stack
├── azure-pipelines.yml          # Azure DevOps (Phase 4-5)
├── .env.example                 # Template (no secrets)
├── .gitignore                   # MUST ignore .env, secrets
├── requirements.txt             # Python dependencies
├── PROJECT-README.txt           # Main project specification
├── PROJECT-SETUP-COMPLETE.md    # GitHub project management setup summary
├── PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md  # PM best practices
├── PHASE-2-READINESS.md         # Phase 2 preparation and requirements
├── user-stories-phased.md       # Complete user story catalog
├── github-project-info.json     # Project metadata
├── AGNTCY-REVIEW.md            # SDK integration guide
├── CLAUDE.md                   # This file
└── README.md                   # Public-facing documentation
```

## Testing Guidance

### Unit Tests (Phase 1)
```python
# Example: Mock AGNTCY SDK components
from unittest.mock import Mock, patch
import pytest

@patch('agntcy_app_sdk.factory.AgntcyFactory')
def test_intent_classification(mock_factory):
    # Test agent logic without real SDK
    pass
```

### Integration Tests (Phase 2)
```python
# Example: Use mock API containers
import pytest
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_services():
    with DockerCompose(".", compose_file_name="docker-compose.test.yml") as compose:
        yield compose

def test_multi_agent_flow(docker_services):
    # Test against mock Shopify/Zendesk/Mailchimp
    pass
```

### Cost Monitoring (Phase 4-5)
```python
# Example: Cost validation in tests
def test_azure_resources_within_budget():
    # Use Azure Pricing API or Cost Management API
    # Assert monthly projected cost < $200
    pass
```

## Disaster Recovery Guidance

### RPO/RTO Targets
- **RPO:** 1 hour (max data loss acceptable)
- **RTO:** 4 hours (max recovery time)

### Backup Strategy (Phase 4-5)
- **Cosmos DB:** Continuous backup, point-in-time restore (30 days)
- **Terraform State:** Azure Blob Storage with versioning (30 day retention)
- **Container Images:** All production images retained indefinitely
- **Key Vault:** Soft-delete (90 days) + purge protection enabled

### DR Testing Schedule
- **Monthly:** Cosmos DB restore validation
- **Quarterly:** Full Terraform destroy/rebuild drill
- **Annually:** Tabletop exercise for all 5 DR scenarios

## Code Style and Conventions

### Python
- **Formatter:** black (line length 100)
- **Linter:** flake8
- **Type Hints:** Use for public APIs, optional for internal
- **Docstrings:** Google style, focus on "why" not "what"
- **Async:** Use async/await for AGNTCY SDK calls

### Comments
- Write for blog readers (educational audience)
- Explain architectural decisions and trade-offs
- Highlight cost optimization rationale
- Reference PROJECT-README.txt sections when relevant

### Naming
- Agents: `{purpose}_agent.py` (e.g., `intent_classification_agent.py`)
- Topics: `{agent-name}` (e.g., `intent-classifier`, `response-generator-en`)
- Containers: `{agent-name}:v{version}-{commit-sha}` (e.g., `intent-classifier:v1.0.0-abc123`)
- Environment vars: `UPPER_SNAKE_CASE` (e.g., `SLIM_ENDPOINT`, `COSMOS_CONNECTION_STRING`)

## Observability

### Phase 1-3 (Local)
- **Stack:** Grafana + ClickHouse + OpenTelemetry Collector (Docker Compose)
- **Endpoints:** Grafana (localhost:3001), OTLP (localhost:4318)
- **Tracing:** Enable via `AgntcyFactory(enable_tracing=True)`

### Phase 4-5 (Azure)
- **Stack:** Azure Monitor + Application Insights + Log Analytics
- **Retention:** 7 days (cost optimization)
- **Metrics:** Agent performance, response times, routing accuracy, costs
- **Alerts:** Latency >2min, error rate >5%, cost >80% budget

## Security Checklist

- [ ] All secrets in Azure Key Vault (Phase 4-5) or .env (Phase 1-3)
- [ ] .env files in .gitignore (never commit secrets)
- [ ] Managed identities for all Azure services (Phase 4-5)
- [ ] TLS 1.3 for all connections
- [ ] Network isolation for backend services (private endpoints)
- [ ] Pre-commit hooks: git-secrets, detect-secrets
- [ ] Dependency scanning: Dependabot, Snyk
- [ ] Secrets rotation procedures documented (quarterly)
- [ ] OWASP ZAP scanning in CI/CD pipeline

## Educational Considerations

This project is designed for a blog post audience. When writing code or documentation:

1. **Clarity over Brevity:** Prefer readable code with explanatory comments
2. **Cost Awareness:** Always explain cost implications of architectural choices
3. **Best Practices:** Demonstrate enterprise patterns (BCDR, IaC, CI/CD) even within budget
4. **Learning Path:** Code should be approachable for developers new to multi-agent systems
5. **Real-World Relevance:** Use realistic scenarios and data (e-commerce, customer service)
6. **Reproducibility:** All steps should be reproducible by blog readers on their own systems

## Common Questions & Answers

**Q: Why not use Azure Functions instead of Container Instances?**
A: Container Instances provide better isolation for long-running agents and align with AGNTCY SDK's design. Functions would require significant adaptation and may not support persistent agent sessions effectively.

**Q: Why Cosmos Serverless instead of provisioned throughput?**
A: Serverless mode provides pay-per-request billing, better for variable/unpredictable workloads, and easier to stay within $200/month budget. Provisioned RU/s has minimum costs even during idle periods.

**Q: Why not use managed Kubernetes (AKS)?**
A: AKS minimum costs (~$70-100/month for control plane + nodes) consume too much of the $200 budget. Container Instances provide adequate orchestration for 5 agents at much lower cost.

**Q: Can we use Azure OpenAI Service?**
A: Yes, but monitor token usage closely. Estimate $20-50/month for testing. Consider using canned responses in Phase 1-3 to avoid costs during development.

**Q: Why SLIM instead of NATS for transport?**
A: SLIM provides enterprise-grade security features out of the box. NATS is excellent for throughput but requires additional security configuration. For educational purposes, SLIM demonstrates secure patterns more clearly.

**Q: How do we handle the Zendesk cost if trial expires?**
A: Three options: (1) Use Zendesk Sandbox for partners/developers (free), (2) Budget $19-49/month and reduce Azure spend to $150-180, (3) Replace with free alternative like osTicket or FreshDesk free tier.

## When Stuck or Uncertain

1. **Check PROJECT-README.txt** for project requirements and constraints
2. **Review AGNTCY-REVIEW.md** for SDK integration patterns
3. **Verify budget impact** for any Azure service suggestion (Phase 4-5)
4. **Ask clarifying questions** about requirements before implementing
5. **Suggest alternatives** with cost/benefit trade-offs
6. **Document decisions** in code comments for blog readers
7. **Test locally first** before deploying to Azure (Phase 1-3 patterns apply to Phase 4-5)

## Success Criteria

The project is successful if:
- ✅ Phase 1-3 runs entirely locally with $0 cloud costs
- ✅ Phase 4-5 stays within $200/month Azure budget
- ✅ All 5 agents communicate via AGNTCY SDK successfully
- ✅ KPIs are measurable and demonstrable (even with mock data in Phase 1-3)
- ✅ Code is educational, well-documented, and reproducible
- ✅ Disaster recovery procedures are tested and validated
- ✅ Security best practices are followed (secrets management, encryption, network isolation)
- ✅ CI/CD pipelines work reliably (GitHub Actions → Azure DevOps)
- ✅ Blog readers can follow along and build it themselves

## Final Notes

- **Priority Order:** Cost constraints > Functionality > Performance > Feature richness
- **Mindset:** This is a learning project - optimize for clarity and education
- **Budget:** $200/month is a HARD LIMIT for Phase 4-5, not a target to maximize
- **Timeline:** No time estimates - focus on what needs to be done, not when
- **Audience:** Developers learning multi-agent AI, Azure, and cost optimization techniques

When in doubt, optimize for:
1. Educational value (blog readers learning)
2. Cost efficiency (demonstrate real-world budget constraints)
3. Reproducibility (readers can build it themselves)
4. Best practices (even within tight constraints)

---

## Recent Updates

### 2026-01-22: GitHub Project Management Integration Complete
- ✅ Created 137 GitHub issues (7 epics + 130 user stories)
- ✅ Configured 30 labels across 5 categories
- ✅ Created 5 phase-based milestones with due dates
- ✅ Automated issue creation via PowerShell scripts (100% success rate)
- ✅ Phase 1 marked as 100% complete
- ✅ Phase 2 readiness document prepared (PHASE-2-READINESS.md)
- ⏳ Awaiting user input to begin Phase 2 implementation

**All work documented in**:
- PROJECT-SETUP-COMPLETE.md (complete GitHub setup summary)
- PHASE-2-READINESS.md (Phase 2 requirements and work breakdown)
- user-stories-phased.md (complete user story catalog)

---

**Last Updated:** 2026-01-22
**Project Phase:** Phase 1 Complete / Phase 2 Ready to Start
**Current Budget Status:** $0 (no cloud resources yet)
**GitHub Project**: https://github.com/orgs/Remaker-Digital/projects/1
