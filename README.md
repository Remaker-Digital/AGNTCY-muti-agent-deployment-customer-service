# AGNTCY Multi-Agent Customer Service Platform

**An educational example project demonstrating cost-effective multi-agent AI systems on Azure**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/actions)
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)]()
[![Phase](https://img.shields.io/badge/phase-6%20Complete-green)]()

## Project Overview

This is an open-source educational project that demonstrates how to build a production-grade multi-agent AI customer service platform using:
- **AGNTCY SDK** for multi-agent orchestration
- **Azure Cloud** for scalable deployment (10,000+ daily users)
- **Docker** for local development
- **Terraform** for infrastructure-as-code
- **Cost optimization** techniques to stay within a $265-360/month budget

This project accompanies a blog post series and serves as a hands-on learning resource for developers interested in:
- Multi-agent architectures and communication patterns
- Azure deployment and cost optimization
- Modern DevOps practices (IaC, CI/CD, observability)
- Building scalable AI-powered customer service systems

## Key Performance Indicators

The platform demonstrates:
- Response time: < 2 seconds P95 (achieved: 0.11ms local, <2s production)
- CSAT score: > 80% target
- Automation rate: > 70% of inquiries
- Cost efficiency: 90-97% savings vs enterprise alternatives
- Scalability: 10,000 daily users with auto-scaling

## Architecture

### 6 Core Agents

| Agent | Purpose | Model |
|-------|---------|-------|
| **Intent Classification** | Routes customer requests to appropriate handlers | GPT-4o-mini |
| **Knowledge Retrieval** | RAG-powered search across merchant content | text-embedding-3-large |
| **Response Generation** | Crafts contextual, on-brand responses | GPT-4o |
| **Escalation** | Identifies cases requiring human intervention | GPT-4o-mini |
| **Analytics** | Monitors performance and generates insights | GPT-4o-mini |
| **Critic/Supervisor** | Content validation for safety and compliance | GPT-4o-mini |

### Technology Stack

| Category | Technology |
|----------|------------|
| **Framework** | AGNTCY SDK (Python 3.12+) |
| **Messaging** | SLIM (Secure Low-Latency Interactive Messaging) |
| **Event Bus** | NATS JetStream |
| **Vector Store** | Azure Cosmos DB (MongoDB API) |
| **Observability** | OpenTelemetry + Azure Application Insights |
| **Cloud** | Microsoft Azure (East US 2) |
| **IaC** | Terraform |
| **CI/CD** | GitHub Actions (dev) → Azure DevOps (prod) |

### Protocol Support

- **A2A (Agent-to-Agent)** - Internal agent communication
- **MCP (Model Context Protocol)** - External tool integrations
- **UCP (Universal Commerce Protocol)** - Shopify/Google commerce standard (Phase 6+)

## Project Phases

### Phase 1-3: Local Development - COMPLETE
- **Budget**: $0/month
- **Status**: All 6 agents implemented, 250 tests, comprehensive documentation

### Phase 4: Azure Infrastructure - COMPLETE
- **Budget**: $265-360/month
- **Status**: All infrastructure deployed (VNet, Cosmos DB, Key Vault, ACR, 9 containers)

### Phase 5: Production Deployment - COMPLETE
- **Budget**: $265-360/month
- **Status**: Azure OpenAI integrated, auto-scaling implemented, security validated

### Phase 6: Multi-Channel & Model Router - COMPLETE
- **Budget**: +$21-36/month additional
- **Theme**: Multi-channel presence with robust authentication

**Completed Features:**
| Feature | Description | Status |
|---------|-------------|--------|
| Customer Authentication | Shopify Customer Accounts API with OAuth 2.0 + PKCE | ✅ Complete |
| Web Widget | Embeddable chat widget (750+ lines, 3 output formats) | ✅ Complete |
| WhatsApp Business | WhatsApp Cloud API integration with webhooks | ✅ Complete |
| Model Router | Azure OpenAI + Anthropic Claude with automatic fallback | ✅ Complete |
| Operational Dashboard | Azure Workbooks with 10 alert rules | ✅ Complete |
| Security Remediation | 15 security findings addressed (BOLA, injection, rate limiting) | ✅ Complete |

**Test Coverage:** 1,178 tests total (85% coverage)

### Phase 7: Platform Expansion (Planned)
- **Budget**: +$27-60/month
- **Theme**: Broader e-commerce and authentication support

**Key Capabilities:**
| Feature | Description |
|---------|-------------|
| WooCommerce Support | WordPress/WooCommerce merchant integration |
| Social Login | Google, Apple, Facebook OAuth |
| Headless API | Custom UI integration for enterprises |
| Multi-Tenant Dashboard | SaaS-ready platform isolation |
| Google Gemini | Third AI provider adapter |
| Document Processing | PDF/DOCX conversion with content cleansing |

### Phase 8: Commerce & Voice (Planned)
- **Budget**: +$60-120/month
- **Theme**: Transactional commerce and voice channel

**Key Capabilities:**
| Feature | Description |
|---------|-------------|
| Voice Channel | Azure Communication Services (PSTN) |
| In-Chat Purchases | Direct transactions in conversation |
| Return Automation | Policy-based automated returns |
| Mobile SDKs | React Native and Flutter support |
| Content Self-Service | Admin UI for RAG configuration |

### Phase 9: Channel Completion (Planned)
- **Budget**: +$25-50/month
- **Theme**: Complete omnichannel coverage

**Key Capabilities:**
| Feature | Description |
|---------|-------------|
| SMS Channel | Twilio/Azure Communication Services |
| Email Channel | Inbound/outbound with threading |
| Social Media | Facebook Messenger, Instagram DM |
| Revenue Attribution | Track AI-influenced sales and ROI |
| Translation API | 50+ language support |

### Phase 10: Enterprise & Scale (Planned)
- **Budget**: +$40-80/month
- **Theme**: Enterprise-ready features and global scale

**Key Capabilities:**
| Feature | Description |
|---------|-------------|
| Multi-Region | Active-active across Azure regions |
| White-Label | Reseller/agency deployment model |
| SOC 2 Type II | Enterprise compliance preparation |
| Enterprise SSO | SAML/OIDC for merchant employees |
| Usage Billing | API metering and tiered access |

### Phase 11: Platform Maturity (Planned)
- **Budget**: +$20-40/month
- **Theme**: Ease-of-use and advanced AI

**Key Capabilities:**
| Feature | Description |
|---------|-------------|
| Visual Flow Builder | Basic no-code conversation design |
| Advanced AI | Sentiment trends, predictive escalation |
| Onboarding Wizard | Self-service merchant setup |
| Performance | Sub-second response optimization |

## Competitive Analysis

Our platform offers significant cost savings compared to enterprise alternatives:

| Platform | Monthly Cost (3K conversations) | Savings |
|----------|--------------------------------|---------|
| **This Platform** | **$265-360** | - |
| Tidio Lyro | $1,559 | 77-83% |
| Intercom + Fin | $3,069 | 88-91% |
| Zendesk + AI | $6,115 | 94-96% |
| Salesforce Agentforce | $7,075 | 95% |
| Ada Enterprise | $10,500 | 97% |

**Unique Differentiators:**
- Multi-agent architecture (6 specialized agents vs monolithic)
- Built-in content validation (Critic agent)
- Full execution tracing for compliance
- Fixed cost model (no per-resolution fees)
- Open standards (AGNTCY, MCP, UCP)
- Self-hosted option with no vendor lock-in

See [Competitive Analysis](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Competitive-Analysis) for full details.

## Quick Start

### Prerequisites

| Requirement | Download URL |
|-------------|--------------|
| Python 3.12+ | [python.org/downloads](https://www.python.org/downloads/) |
| Docker Desktop | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Git | [git-scm.com/downloads](https://git-scm.com/downloads) |

### Installation

```bash
# Clone the repository
git clone https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service.git
cd AGNTCY-muti-agent-deployment-customer-service

# Set up Python virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
copy .env.example .env

# Start infrastructure services
docker-compose up -d

# Verify services
docker-compose ps
```

### Development Console

```bash
# Start the interactive console
streamlit run console/app.py --server.port 8080

# Access at http://localhost:8080
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=shared --cov-report=html

# Current: 1,178 tests, 85% coverage
```

## Project Structure

```
.
├── agents/                      # 6 Agent implementations
│   ├── intent_classification/
│   ├── knowledge_retrieval/
│   ├── response_generation/
│   ├── escalation/
│   ├── analytics/
│   └── critic_supervisor/
├── mocks/                       # Mock APIs (Phase 1-3)
├── shared/                      # Shared utilities
│   ├── factory.py              # AGNTCY factory singleton
│   ├── base_agent.py           # Shared agent boilerplate
│   ├── openai_pool.py          # Connection pooling
│   └── cosmosdb_pool.py        # Database client
├── console/                     # Streamlit dev console
├── content/                     # RAG content and templates
│   └── templates/              # Merchant content templates
├── scripts/                     # Operational scripts
│   └── content_manager/        # RAG ingestion tool
├── tests/                       # Test suites (1,178 tests)
├── terraform/                   # Infrastructure as Code
│   └── phase4_prod/            # Azure production
├── evaluation/                  # AI model evaluation
│   ├── prompts/                # Production prompts
│   ├── datasets/               # Test datasets
│   └── results/                # Evaluation reports
├── docs/                        # Documentation
└── docker-compose.yml          # Local dev stack
```

## Documentation

### Wiki

- [Home](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki)
- [Architecture](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Architecture)
- [Scalability](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Scalability)
- [Model Context Protocol](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Model-Context-Protocol)
- [UCP Integration Guide](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/UCP-Integration-Guide)
- [Merchant Content Management](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Merchant-Content-Management)
- [Competitive Analysis](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Competitive-Analysis)

### Key Documents

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | AI assistant guidance and project context |
| [AGNTCY-REVIEW.md](AGNTCY-REVIEW.md) | SDK integration patterns |
| [docs/PHASE-6-7-PLANNING-DECISIONS.md](docs/PHASE-6-7-PLANNING-DECISIONS.md) | Roadmap decisions |
| [docs/COMPETITIVE-ANALYSIS.md](docs/COMPETITIVE-ANALYSIS.md) | Market comparison |

## Cost Optimization

### Current Production Costs (~$265-360/month)

| Category | Monthly Cost |
|----------|--------------|
| Azure Container Apps | $80-120 |
| Azure OpenAI API | $48-62 |
| Cosmos DB Serverless | $30-50 |
| Application Insights | $32-43 |
| Key Vault, ACR, Networking | $20-30 |
| **Total** | **$265-360** |

### Cost Strategies

- Container Apps with scale-to-zero (vs always-on ACI)
- Cosmos DB Serverless (pay-per-request)
- GPT-4o-mini for classification tasks (10x cheaper than GPT-4o)
- 7-day log retention
- Connection pooling for external APIs
- Intelligent trace sampling (50%)

## Security

- **PII Tokenization**: All data tokenized before third-party AI calls
- **Content Validation**: Critic agent blocks prompt injection and harmful content
- **Secrets Management**: Azure Key Vault with managed identities
- **Network Isolation**: Private VNet for all backend services
- **Security Scanning**: OWASP ZAP, Snyk, Dependabot
- **Input Sanitization**: 30+ prompt injection patterns detected and blocked
- **Rate Limiting**: Sliding window rate limiter (30 req/min per session)
- **PII Scrubbing**: Automatic redaction of emails, phones, IDs in logs
- **BOLA Protection**: Authorization header validation in all mock APIs

### Security Remediation (January 2026)

15 security findings addressed:
- ✅ Unauthenticated chat endpoint → Session validation added
- ✅ BOLA vulnerabilities → Authorization headers required
- ✅ Prompt injection → Input sanitization module
- ✅ Rate limiting → Sliding window algorithm
- ✅ PII in logs → Automatic scrubbing
- ✅ Default confidence → Changed from 1.0 to 0.5

See [Security Remediation Report](docs/SECURITY-REMEDIATION-2026-01-28.md)

## Contributing

This is an educational project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues)
- **Wiki**: [Project Wiki](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki)
- **Blog**: [remakerdigital.com/blog](https://www.remakerdigital.com/home/blog/)
- **Email**: mike@remakerdigital.com

---

**Status**: Phase 6 Complete ✅

**Last Updated**: 2026-01-28

**Current Milestone**: Phase 6 complete - Multi-channel & Model Router

**Completed This Phase**:
- Shopify Customer Accounts API (OAuth 2.0 + PKCE)
- Embeddable JavaScript chat widget
- WhatsApp Business Cloud API integration
- Model Router (Azure OpenAI + Anthropic fallback)
- Azure Workbooks operational dashboard (10 alerts)
- Security remediation (15 findings addressed)

**Next Milestone**: Phase 7 - Platform Expansion (WooCommerce, Social Login, Headless API)

**Infrastructure**: 9/9 containers running, auto-scaling implemented, 10,000 daily user capacity

**Test Count**: 1,178 tests (85% coverage)
