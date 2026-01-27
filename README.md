# AGNTCY Multi-Agent Customer Service Platform

**An educational example project demonstrating cost-effective multi-agent AI systems on Azure**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/yourusername/agntcy-multi-agent-customer-service/actions)
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)]()
[![Phase](https://img.shields.io/badge/phase-1-green)]()

## 📚 Project Overview

This is an open-source educational project that demonstrates how to build a production-grade multi-agent AI customer service platform using:
- **AGNTCY SDK** for multi-agent orchestration
- **Azure Cloud** for scalable deployment
- **Docker** for local development
- **Terraform** for infrastructure-as-code
- **Cost optimization** techniques to stay within a $310-360/month budget (revised from $200)

This project accompanies a blog post series and serves as a hands-on learning resource for developers interested in:
- Multi-agent architectures and communication patterns
- Azure deployment and cost optimization
- Modern DevOps practices (IaC, CI/CD, observability)
- Building scalable AI-powered customer service systems

## 🎯 Key Performance Indicators

The platform aims to demonstrate:
- ⚡ Response time: < 2 minutes (down from 18 hours)
- 😊 CSAT score: > 80% (up from 62%)
- 🛒 Cart abandonment: < 30% (down from 47%)
- 🤖 Automation rate: > 70% of inquiries
- 📈 Conversion rate: +50% increase
- 💰 Cost reduction: 40% while improving quality

## 🏗️ Architecture

### 6 Core Agents (Added Critic/Supervisor 2026-01-22)
1. **Intent Classification Agent** - Routes customer requests
2. **Knowledge Retrieval Agent** - Searches documentation
3. **Response Generation Agent** - Crafts contextual responses
4. **Escalation Agent** - Identifies human-needed cases
5. **Analytics Agent** - Monitors performance
6. **Critic/Supervisor Agent** - Content validation for safety and compliance (input/output validation)

### Technology Stack
- **Framework**: AGNTCY SDK (Python 3.12+)
- **Messaging**: SLIM (Secure Low-Latency Interactive Messaging)
- **Observability**: OpenTelemetry + Grafana + ClickHouse
- **Cloud**: Microsoft Azure (East US region)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions (dev) → Azure DevOps (prod)

## 📋 Project Phases

### Phase 1: Infrastructure & Containers 🟢 100% Complete
- **Budget**: $0/month (local development)
- **Deliverable**: Containerized framework with mock APIs and agent implementations
- **Status**: ✅ All components complete, CI/CD pipeline integrated

### Phase 2: Business Logic 🟢 95% Complete
- **Budget**: $0/month (local development)
- **Deliverable**: Full agent implementations
- **Status**: ✅ 5 core agents implemented, 96% integration test pass rate, intentional 5% deferred to Phase 4

### Phase 3: Testing & Validation 🟢 100% Complete (Current)
- **Budget**: $0/month (local development)
- **Deliverable**: Comprehensive test suite
- **Status**: ✅ 152 test scenarios executed (81% pass rate), performance benchmarks established, documentation complete

### Phase 4: Azure Production Setup
- **Budget**: $310-360/month (revised from $200)
- **Deliverable**: Production-ready infrastructure

### Phase 5: Deployment & Go-Live
- **Budget**: $310-360/month (revised from $200)
- **Deliverable**: Live system with monitoring

## 🚀 Quick Start

### Prerequisites

**Required (Phase 1-3):**

| Requirement | Download URL | Documentation |
|-------------|--------------|---------------|
| Windows 11 (or compatible OS) | - | - |
| Python 3.12+ | [python.org/downloads](https://www.python.org/downloads/) | [Python Docs](https://docs.python.org/3/) |
| Docker Desktop | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | [Docker Docs](https://docs.docker.com/) |
| Git | [git-scm.com/downloads](https://git-scm.com/downloads) | [Git Docs](https://git-scm.com/doc) |
| VS Code (recommended) | [code.visualstudio.com](https://code.visualstudio.com/) | [VS Code Docs](https://code.visualstudio.com/docs) |

**Optional (Phase 4-5 Production):**

| Service | Sign-Up URL | Free Tier |
|---------|-------------|-----------|
| Azure Subscription | [azure.microsoft.com/free](https://azure.microsoft.com/free) | $200 credit |
| Shopify Partners | [shopify.com/partners](https://www.shopify.com/partners) | Free |
| Zendesk | [zendesk.com/register](https://www.zendesk.com/register) | 14-day trial |
| Mailchimp | [mailchimp.com/signup](https://mailchimp.com/signup/) | 250 contacts |
| Google Analytics | [analytics.google.com](https://analytics.google.com) | Free |

See [SETUP-GUIDE.md](SETUP-GUIDE.md) for detailed installation instructions and [CLAUDE.md](CLAUDE.md) for API key locations.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/agntcy-multi-agent-customer-service.git
   cd agntcy-multi-agent-customer-service
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment variables**
   ```bash
   copy .env.example .env
   # Edit .env with your local configuration
   ```

5. **Start infrastructure services**
   ```bash
   docker-compose up -d
   ```

6. **Verify services are running**
   ```bash
   docker-compose ps
   ```

   You should see:
   - `agntcy-nats` (NATS messaging)
   - `agntcy-slim` (SLIM transport)
   - `agntcy-clickhouse` (observability database)
   - `agntcy-otel-collector` (telemetry aggregation)
   - `agntcy-grafana` (dashboards)
   - Mock APIs (Shopify, Zendesk, Mailchimp, Google Analytics)
   - Agent containers (Intent, Knowledge, Response, Escalation, Analytics)

7. **Start the Development Console**
   ```bash
   # Interactive development and testing console
   .\start-console.ps1
   
   # Or manually with Streamlit
   streamlit run console/app.py --server.port 8080
   ```

8. **Access the interfaces**

   **Development Console**: http://localhost:8080
   - Interactive chat interface with test personas
   - Real-time agent metrics and performance monitoring
   - Conversation trace viewer and system status
   - Primary interface for development and testing

   **Grafana Dashboards**: http://localhost:3001
   - Username: `admin`, Password: `admin`
   - System-wide observability and analytics

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit -v

# Run integration tests only
pytest tests/integration -v

# Run with coverage report
pytest tests/ --cov=agents --cov=shared --cov-report=html
# View coverage: open htmlcov/index.html

# Current test status: 67 passing, 5 skipped, 31% coverage
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent-intent-classification

# AGNTCY infrastructure
docker-compose logs -f slim nats otel-collector
```

## 📁 Project Structure

```
.
├── console/                     # Development Console (Phase 2+)
│   ├── app.py                  # Streamlit console application
│   ├── agntcy_integration.py   # Real AGNTCY system integration
│   ├── requirements.txt        # Console dependencies
│   ├── Dockerfile             # Console container
│   └── README.md              # Console documentation
├── agents/                      # Agent implementations
│   ├── intent_classification/
│   ├── knowledge_retrieval/
│   ├── response_generation/
│   ├── escalation/
│   └── analytics/
├── mocks/                       # Mock APIs (Phase 1-3)
│   ├── shopify/
│   ├── zendesk/
│   ├── mailchimp/
│   └── google-analytics/
├── shared/                      # Shared utilities
│   ├── factory.py              # AGNTCY factory singleton
│   ├── models.py               # Message models
│   └── utils.py
├── tests/                       # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── test-data/                   # Test fixtures
├── config/                      # Service configurations
│   ├── slim/
│   ├── otel/
│   └── grafana/
├── terraform/                   # Infrastructure as Code
│   ├── phase1_dev/
│   └── phase4_prod/
├── .github/workflows/          # GitHub Actions CI
├── docs/                        # Documentation
├── start-console.ps1           # Console startup script
├── docker-compose.yml          # Local dev stack
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── PROJECT-README.txt          # Detailed specifications
├── AGNTCY-REVIEW.md           # SDK integration guide
├── CLAUDE.md                   # AI assistant guidance
└── README.md                   # This file
```

## 🧪 Development Workflow

### Phase 1 Tasks (100% Complete ✅)
- [x] Project structure created
- [x] Docker Compose configuration
- [x] AGNTCY infrastructure services
- [x] Mock API implementations (all 4 complete)
- [x] Shared utilities and factory
- [x] Agent implementations (all 5 complete)
- [x] Unit and integration test framework
- [x] GitHub Actions CI workflow complete

### Working on an Agent

1. Navigate to agent directory: `cd agents/intent_classification`
2. Edit `agent.py` for business logic
3. Update `requirements.txt` if adding dependencies
4. Write tests in `tests/unit/test_intent_classification.py`
5. Build and test: `docker-compose build agent-intent-classification`
6. View logs: `docker-compose logs -f agent-intent-classification`

### Adding a New Mock API Endpoint

1. Edit mock service file (e.g., `mocks/shopify/app.py`)
2. Add test fixture in `test-data/shopify/`
3. Rebuild container: `docker-compose build mock-shopify`
4. Test endpoint: `curl http://localhost:8001/your-endpoint`

## 📊 Monitoring & Observability

### Grafana Dashboards
Access at http://localhost:3001 (admin/admin)

**Available Views:**
- Agent performance metrics
- Message throughput
- Response times
- Error rates
- Cost tracking (Phase 4-5)

### OpenTelemetry Traces
- View distributed traces in Grafana
- Track message flow across agents
- Identify bottlenecks

### Logs
```bash
# ClickHouse query interface
curl http://localhost:8123 --data "SELECT * FROM otel.otel_logs LIMIT 10"
```

## 💰 Cost Optimization

### Phase 1-3 (Local Development): $0/month
- All services run on Docker Desktop
- No cloud resources provisioned
- Mock APIs eliminate external service costs

### Phase 4-5 (Azure Production): $310-360/month target (revised)
Key strategies:
- Azure Container Instances (pay-per-second)
- Cosmos DB Serverless (pay-per-request)
- Redis Basic C0 tier (250MB)
- 7-day log retention
- Auto-scaling down to 1 instance
- Single region (East US)

See `docs/cost-optimization.md` for detailed breakdown.

## 🔒 Security

- **Secrets**: Never commit `.env` file. Use `.env.example` as template.
- **Pre-commit hooks**: Install with `pre-commit install`
- **Scanning**: Bandit (Python), Dependabot (dependencies)
- **TLS**: Required in Phase 4-5 (disabled locally for convenience)

## 🧩 Integration with Third-Party Services

### Phase 1-3: Mock APIs (No accounts needed)
All external services are mocked locally.

### Phase 4-5: Real APIs (Accounts required)

| Service | Sign-Up URL | Cost | API Key Location |
|---------|-------------|------|------------------|
| **Shopify** | [shopify.com/partners](https://www.shopify.com/partners) | Free | Partner Dashboard → Apps → API credentials |
| **Zendesk** | [zendesk.com/register](https://www.zendesk.com/register) | Free trial | Admin → APIs → Zendesk API |
| **Mailchimp** | [mailchimp.com/signup](https://mailchimp.com/signup/) | Free (250) | Account → Extras → API keys |
| **Google Analytics** | [analytics.google.com](https://analytics.google.com) | Free | [console.cloud.google.com](https://console.cloud.google.com) → IAM → Service Accounts |
| **Azure** | [azure.microsoft.com/free](https://azure.microsoft.com/free) | ~$310-360/month | [portal.azure.com](https://portal.azure.com) → Resource → Keys |

> **Full Setup Instructions**: See [CLAUDE.md](CLAUDE.md#third-party-service-accounts-required) for complete sign-up procedures, required permissions, and API key locations.

## 🤝 Contributing

This is an educational project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please read `CONTRIBUTING.md` for details on our code of conduct and development process.

## 📖 Documentation

- **[PROJECT-README.txt](PROJECT-README.txt)** - Comprehensive project specifications
- **[AGNTCY-REVIEW.md](AGNTCY-REVIEW.md)** - AGNTCY SDK integration guide
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidance
- **[docs/](docs/)** - Additional documentation
  - Agent architecture
  - Message flow diagrams
  - Testing strategy
  - Deployment guide
  - Cost optimization details
  - Disaster recovery procedures

## 🐛 Troubleshooting

### Docker Compose Issues
```bash
# Rebuild all containers
docker-compose build --no-cache

# Reset everything
docker-compose down -v
docker-compose up -d
```

### AGNTCY SDK Connection Issues
- Verify SLIM is running: `curl http://localhost:46357`
- Check NATS: `curl http://localhost:8222/varz`
- Review logs: `docker-compose logs slim nats`

### Port Conflicts
If ports are already in use, edit `docker-compose.yml` to change mappings.

## 📚 Learning Resources

| Resource | URL | Description |
|----------|-----|-------------|
| **AGNTCY SDK** | [github.com/agntcy/app-sdk](https://github.com/agntcy/app-sdk) | Multi-agent orchestration framework |
| **AGNTCY Docs** | [docs.agntcy.com](https://docs.agntcy.com) | Official SDK documentation |
| **Azure Architecture** | [learn.microsoft.com/azure/architecture](https://learn.microsoft.com/azure/architecture/) | Cloud design patterns |
| **Azure OpenAI** | [learn.microsoft.com/azure/ai-services/openai](https://learn.microsoft.com/azure/ai-services/openai/) | LLM integration guides |
| **Terraform Azure** | [registry.terraform.io/providers/hashicorp/azurerm](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) | Infrastructure as Code |
| **Blog Series** | [remakerdigital.com/blog](https://remakerdigital.com/blog/) | Project tutorials |

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- AGNTCY team for the excellent multi-agent SDK
- Microsoft Azure documentation and best practices
- Open-source community for tools and libraries

## 📞 Contact & Support

- **Issues**: Open a GitHub issue
- **Discussions**: GitHub Discussions
- **Blog**: https://www.remakerdigital.com/home/blog/
- **Email**: mike@remakerdigital.com

---

**Status**: 🟢 Phase 3 - 100% Complete ✅

**Last Updated**: 2026-01-25

**Next Milestone**: Phase 4 - Azure Production Setup (Infrastructure, Real APIs, Multi-Language Support)

**Test Coverage**: 50% (152 test scenarios, 81% overall pass rate)
- Unit tests: 67 passing
- Integration tests: 25/26 passing (96% pass rate)
- E2E tests: 20 scenarios (5% baseline, expected for template responses)
- Multi-turn tests: 10 scenarios (30% pass rate)
- Performance: 0.11ms P95 response time, 3,071 req/s throughput
