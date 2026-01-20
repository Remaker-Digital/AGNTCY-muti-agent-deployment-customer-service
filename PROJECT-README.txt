# This document was written by me based on iterative evaluations and questioning by Claude Code over several iterations.
# Once I was satisfied with the content, I started a new session and asked Claude Code to examine the PROJECT-README.txt and create a CLAUDE.md file.
# Once the Claude.md file was ready, I reviewed it in detail and made manual changes or called out TODO items where I felt that important details were missing.

PROJECT PURPOSE:
This is an educational example project demonstrating how to build a multi-agent AI system on Azure using the AGNTCY SDK. This project will be publicly available on GitHub as a companion to a blog post series, serving as a hands-on learning tool for developers interested in multi-agent architectures, Azure deployment, and cost-effective cloud solutions.

OBJECTIVE:
- An AI-powered multi-channel customer engagement platform that can automate routine interactions, provide personalized experiences, and intelligently route complex issues while maintaining high-quality customer service.

KEY PERFORMANCE INDICATORS
- Reduce average response time from 18 hours to under 2 minutes
- Improve CSAT from 62% to above 80%
- Decrease cart abandonment rate from 47% to under 30%
- Automate resolution of 70%+ routine customer inquiries
- Increase conversion rate by at least 50%
- Reduce customer support costs by 40% while improving service quality

TECHNICAL CONSTRAINTS:
- Must integrate seamlessly with existing Shopify store
- Zendesk for ticket-based customer support
- Mailchimp for email marketing campaigns
- Google Analytics for basic website analytics
- Cannot disrupt checkout flow or site performance
- Need mobile-responsive chatbot interface
- Primary language: US English
- Additional language support (Phase 4): Canadian French, Spanish (see MULTI-LANGUAGE SUPPORT section)
- Real-time inventory integration for product inquiries
- Maintain sub-2-second page load times

BUDGET:
- Phase 1-3 (Development & Testing): $0/month
  * Local development using Docker Desktop on Windows 11
  * All services run locally via Docker Compose
  * Mock/stub APIs for third-party integrations
  * No cloud resources consumed

- Phase 4-5 (Production Deployment): $200/month
  * Azure resources deployed to East US region
  * Cost optimization is a key learning objective
  * Budget alerts at 80% ($160) and 95% ($190)
  * Cost allocation tags for granular tracking

PLAN:
- Phase 1: Create the infrastructure and deployable containers with all essential software, excluding the business logic of the application suitable for desktop development and testing using Docker Desktop on Windows 11
  * Setup: VS Code, Docker Desktop, GitHub Desktop, AGNTCY SDK (PyPI installation)
  * Deliverable: Containerized agent framework with mock APIs
  * Testing: Unit tests with pytest, no external service dependencies
  * Budget: $0 (fully local)

- Phase 2: Implement the business logic of the service
  * Development: Agent implementation using AGNTCY SDK patterns
  * Integration: Mock Shopify, Zendesk, Mailchimp APIs
  * Testing: Integration tests against mock services
  * Budget: $0 (fully local)

- Phase 3: Test the business logic of the service for functionality
  * Functional testing with mock data
  * Multi-agent conversation flows
  * Performance benchmarking (local)
  * CI: GitHub Actions for automated testing
  * Budget: $0 (GitHub Actions free for public repos)

- Phase 4: Create a new version of the project adapted to a full production environment on Azure
  * Region: East US (primary)
  * Multi-language support: Add Canadian French and Spanish
  * Real API integration: Shopify, Zendesk, Mailchimp
  * Infrastructure: Terraform for Azure resources
  * CI/CD: Azure DevOps Pipelines
  * Budget: $200/month with aggressive cost optimization

- Phase 5: Deploy and test the production environment before go-live
  * End-to-end testing in Azure
  * Load testing and performance validation
  * Security scanning and compliance checks
  * Disaster recovery validation
  * Budget: Within $200/month allocation

DEVELOPMENT ENVIRONMENT:
- Operating System: Windows 11
- IDE: Visual Studio Code (VS Code)
- Containerization: Docker Desktop for Windows
- Version Control: GitHub Desktop and GitHub repository
- Programming Language: Python 3.12+
- Package Management: pip (with virtual environments)

TECHNOLOGY STACK:
- AGNTCY SDK: Multi-agent infrastructure for collaboration, discovery, identity, messaging, and observability
  * Installation: pip install agntcy-app-sdk (PyPI)
  * Source: https://github.com/agntcy/app-sdk
  * Version: Latest stable from PyPI

- GitHub: Version control and collaboration
  * GitHub Desktop for local Git operations
  * GitHub Actions for CI/CD (Phase 1-3)
  * Public repository for educational access

- Docker: Fully containerized infrastructure
  * Docker Desktop for Windows for local development
  * Docker Compose for multi-service orchestration
  * Container images for each agent and supporting services

- Azure: Cloud platform for production deployment (Phase 4-5)
  * Primary Region: East US
  * Services detailed in PRODUCTION ARCHITECTURE section

- Terraform: Infrastructure-as-code for Azure resource provisioning
  * Defines all Azure resources declaratively
  * Version controlled alongside application code
  * Separate configurations for dev (Phase 1-3) and prod (Phase 4-5)

AGENTS:
- Intent Classification Agent: Routes incoming requests to appropriate handlers
- Knowledge Retrieval Agent: Searches internal documentation and knowledge bases
- Response Generation Agent: Crafts contextually appropriate responses
- Escalation Agent: Identifies cases requiring human intervention
- Analytics Agent: Monitors performance and identifies improvement opportunities
- Additional agents as required

PRODUCTION ARCHITECTURE (Phase 4-5 only):
- Region: East US (primary deployment region)
- Containerized AI agents running on Azure Container Instances
- Azure Cosmos DB for conversation state storage (optimized to fit $200/month budget)
- Azure Cache for Redis for session management (Basic tier for cost optimization)
- Azure Application Gateway for load balancing (Standard_v2 tier)
- Azure Container Registry for image storage (Basic tier)
- Azure Key Vault for secrets management (Standard tier)
- Azure Monitor for observability (with cost-optimized retention policies)
- Azure Cognitive Search integration for the Knowledge Retrieval Agent (Basic tier)

Note: All services sized and configured to maximize functionality within $200/month budget constraint. See COST OPTIMIZATION section for specific strategies.

NETWORKING (Phase 4-5):
- Virtual network with private endpoints for database and cache
- Network security groups with least-privilege access
- Public endpoint only for Application Gateway
- Internal service mesh for agent communication
- Single region deployment (East US) for cost optimization
- Note: Azure Front Door global load balancing excluded to stay within budget (can be added later if needed)

SCALABILITY (Phase 4-5):
- Each agent should scale independently based on CPU/memory
- Auto-scaling: Start with 1 instance, scale to max 3 instances per agent (reduced from 2-10 for cost optimization)
- Redis cache: Basic C0 (250MB) initially, upgrade if needed within budget
- Cosmos DB: Serverless mode for cost optimization (pay-per-request vs provisioned RU/s)
- Horizontal scaling limited by $200/month budget constraint

SECURITY:
- All secrets stored in Key Vault
- Managed identities for all services
- Encryption at rest for storage
- TLS 1.3 for all connections
- Network isolation for backend services

OBSERVABILITY:
- Application Insights for APM
- Log Analytics workspace for centralized logging
- Custom metrics for agent performance
- Alerts for latency, errors, and cost anomalies

COST OPTIMIZATION (Key Learning Objective):
Phase 1-3 Strategies ($0 budget):
- Use Docker Desktop for all local development
- Mock/stub all third-party services (no API costs)
- GitHub Actions free tier for public repositories
- No cloud resources provisioned

Phase 4-5 Strategies ($200/month budget):
- Use Azure Container Instances (pay-per-second billing) instead of always-on App Service
- Cosmos DB Serverless mode (pay-per-request) instead of provisioned throughput
- Redis Basic C0 tier (250MB) for minimal session caching needs
- Container Registry Basic tier (10GB storage)
- Application Gateway Standard_v2 with minimal capacity units
- Auto-shutdown during low-traffic hours (e.g., 2am-6am ET)
- Aggressive auto-scaling down to 1 instance per agent during idle periods
- 7-day log retention in Log Analytics (vs 30-day default)
- Exclude Azure Front Door, Traffic Manager, and other premium services
- Budget alerts at 80% ($160) and 95% ($190) with email notifications
- Cost allocation tags by agent type and environment for granular tracking
- Weekly cost review and optimization iterations
- Use B-series burstable VMs if needed (cost-effective for variable workloads)

Cost Estimation Tool:
- Azure Pricing Calculator estimates to be documented in deployment guide
- Target: ~$180/month average with $200 ceiling

CI/CD PIPELINE:
Phase 1-3 (GitHub Actions - Free for public repos):
- Workflow: .github/workflows/dev-ci.yml
- Triggers: Push to main, pull requests
- Jobs:
  * Lint Python code (flake8, black)
  * Unit tests (pytest with coverage reports)
  * Integration tests against mock services
  * Docker image builds (validate only, not pushed)
  * Security scanning (Dependabot, Bandit for Python)
- Artifacts: Test coverage reports, build logs
- Badge: Build status in README.md

Phase 4-5 (Azure DevOps Pipelines):
- Pipeline: azure-pipelines.yml
- Triggers: Push to production branch, manual release approval
- Stages:
  * Build: Container images pushed to Azure Container Registry
  * Deploy to Staging: Terraform apply for staging environment
  * Integration Tests: Against real Azure resources (staging)
  * Deploy to Production: Manual approval gate, Terraform apply
  * Smoke Tests: Validate production deployment
- Secrets: Stored in Azure Key Vault, accessed via service principals
- Notifications: Slack/email on deployment success/failure

BACKUP AND DISASTER RECOVERY:
Scope: Comprehensive BCDR planning to demonstrate enterprise best practices within budget constraints

Recovery Objectives:
- RPO (Recovery Point Objective): 1 hour
- RTO (Recovery Time Objective): 4 hours
- Acceptable data loss: Maximum 1 hour of conversation history

Phase 1-3 Backup Strategy (Local Development):
- Version Control: All code, configurations, and IaC in GitHub
  * Automatic versioning via Git commits
  * Branch protection rules on main branch
  * Minimum 2 reviewers for production code
- Docker Images: Tagged and versioned in docker-compose.yml
- Mock Data: Stored in /test-data directory, version controlled
- Configuration: All .env.example files in repository (no secrets)
- Local Backups: Development machine automated backups (Windows Backup to external drive recommended)

Phase 4-5 Backup Strategy (Azure Production):
Infrastructure Backups:
- Terraform State: Stored in Azure Blob Storage with versioning enabled
  * State file backup retention: 30 days
  * State locking via Azure Blob lease to prevent conflicts
- Infrastructure-as-Code: All Terraform configs in GitHub (version controlled)

Data Backups:
- Cosmos DB:
  * Continuous backup mode enabled (point-in-time restore up to 30 days)
  * Automatic backups every 1 hour
  * Geo-redundant backup storage (if within budget, otherwise LRS)
  * Restore testing: Monthly validation of restore procedures
- Redis Cache:
  * Session data is ephemeral and can be regenerated
  * Redis persistence (RDB snapshots) every 15 minutes to storage account
  * Backup retention: 7 days (cost optimization)
- Azure Storage (logs, artifacts):
  * Geo-redundant storage (GRS) for critical artifacts
  * Lifecycle management: Move to cool tier after 30 days, archive after 90 days

Application Backups:
- Container Images:
  * All images tagged with version and commit SHA
  * Retention policy: Keep all production images indefinitely, cleanup dev images after 30 days
  * Azure Container Registry geo-replication disabled (cost optimization)
- Configuration:
  * Key Vault: Automatic soft-delete (90-day retention) and purge protection enabled
  * Secrets versioned automatically in Key Vault

Disaster Recovery Procedures:
1. Infrastructure Failure:
   - Terraform re-apply from latest state (estimated 30 minutes)
   - DNS/traffic routing to healthy resources (if multi-region in future)

2. Data Corruption/Loss:
   - Cosmos DB point-in-time restore to last known good state
   - Estimated restoration time: 2-3 hours for full dataset

3. Regional Outage (East US):
   - Phase 4-5 single region deployment: Accept downtime until region recovers
   - Future enhancement: Multi-region with failover (requires budget increase)

4. Accidental Deletion:
   - Resource locks on critical resources (Cosmos DB, Storage, Key Vault)
   - Azure Resource Manager soft-delete enabled where available
   - Terraform state history for infrastructure rollback

5. Security Incident:
   - Key Vault key rotation procedures documented
   - Compromised container image: Roll back to previous known-good image
   - Access audit logs in Log Analytics (retained 7 days)

Testing Schedule:
- Monthly: Backup restore validation (select Cosmos DB collection)
- Quarterly: Full disaster recovery drill (Terraform destroy and rebuild in test subscription)
- Annually: Tabletop exercise for all DR scenarios
- Document all DR tests in /docs/dr-test-results/

Monitoring and Alerts:
- Azure Backup failure alerts → immediate notification
- Terraform state file modified → audit log entry
- Cosmos DB backup age > 2 hours → warning alert
- Key Vault access from unexpected IP → security alert

MULTI-LANGUAGE SUPPORT:
Primary Language: US English (all phases)
- All documentation, code comments, log messages, and UI text in US English
- Default agent responses in US English

Additional Languages (Phase 4 only): Canadian French, Spanish
- Implementation Strategy:
  * Language detection in Intent Classification Agent (use metadata field: {"language": "fr-CA"})
  * Separate response generation agents per language:
    - response-generator-en (US English) - default
    - response-generator-fr-ca (Canadian French)
    - response-generator-es (Spanish)
  * Agent topic-based routing: Intent agent routes to language-specific response agent
  * Translation approach: Pre-translated response templates (not real-time translation to reduce cost)
  * Knowledge base: Multilingual documents in Azure Cognitive Search with language field

- Phase 1-3: US English only (simplifies development and testing)
- Phase 4: Add Canadian French and Spanish support
  * Requires: Translated knowledge base content
  * Requires: Language-specific response templates
  * Testing: Mock conversations in all three languages

- Cost Considerations:
  * No third-party translation APIs (cost prohibitive)
  * Static translations provided as part of knowledge base setup
  * Language-specific agent instances only spun up when needed (auto-scaling)

TESTING STRATEGY:
Phase 1 - Unit Testing (No External Dependencies):
- Framework: pytest with coverage reporting
- Scope: Individual agent logic, message parsing, routing decisions
- Mocks: All AGNTCY SDK transports and protocols mocked
- Coverage Target: >80% code coverage
- Environment: Local Windows 11 + VS Code + Docker Desktop
- CI: GitHub Actions runs tests on every commit
- No API keys or external services required

Phase 2 - Integration Testing (Mock APIs):
- Framework: pytest with pytest-docker for container orchestration
- Mock Services (implemented as Docker containers):
  * Mock Shopify API: /mocks/shopify/
    - Endpoints: /products, /inventory, /orders, /cart
    - Responses: Static JSON fixtures in /test-data/shopify/
  * Mock Zendesk API: /mocks/zendesk/
    - Endpoints: /tickets, /users, /ticket/{id}/comments
    - Responses: Static JSON fixtures in /test-data/zendesk/
  * Mock Mailchimp API: /mocks/mailchimp/
    - Endpoints: /campaigns, /lists, /automations
    - Responses: Static JSON fixtures in /test-data/mailchimp/
  * Mock Google Analytics: /mocks/google-analytics/
    - Endpoints: /reports, /events
    - Responses: Static JSON fixtures in /test-data/analytics/
- Test Scenarios:
  * Multi-agent conversation flows (customer inquiry → response)
  * Intent classification → knowledge retrieval → response generation pipeline
  * Escalation triggers and human handoff
  * Session management and context preservation
  * Error handling and retry logic
- Environment: Docker Compose orchestrates all agents + mock services
- CI: GitHub Actions builds all containers and runs integration suite
- No real API keys required (all mocked)

Phase 3 - Functional Testing (End-to-End Local):
- Framework: pytest + Playwright for chatbot UI testing (if applicable)
- Scope: Complete customer journey simulations
- Test Data: Realistic customer conversation scripts in /test-data/conversations/
- Performance: Benchmark response times, throughput on local hardware
- Load Testing: Locust for concurrent user simulation (limited by local resources)
- CI: GitHub Actions runs nightly full regression suite
- Deliverable: Test report demonstrating all KPIs met in local environment

Phase 4 - Production Integration Testing (Real APIs):
- Environment: Azure staging environment (separate from production)
- Real API Integration:
  * Shopify: Developer/Partner account (free) with test store
    - Required: Shopify Partner account (free)
    - API Key: Stored in Azure Key Vault
    - Scope: Read products, inventory; simulate orders in test mode
  * Zendesk: Trial or Sandbox account
    - Required: Zendesk trial account (free 14-day trial or sandbox)
    - API Key: Stored in Azure Key Vault
    - Scope: Create/update/read test tickets only
  * Mailchimp: Free tier account
    - Required: Mailchimp free account (up to 500 contacts)
    - API Key: Stored in Azure Key Vault
    - Scope: Test campaigns to internal email addresses only
  * Google Analytics: Test property
    - Required: Google Analytics test property (free)
    - Service Account: Stored in Azure Key Vault
    - Scope: Read-only access to test data
- Testing Scope:
  * API authentication and authorization
  * Real data payloads (validation of mock API accuracy)
  * Rate limiting and error handling
  * Webhook delivery and processing
- CI/CD: Azure DevOps Pipeline runs integration tests on staging before production deploy
- Cost: Minimal (free tiers + small Azure staging environment ~$20-30/month)

Phase 5 - Production Validation Testing:
- Smoke Tests: Automated post-deployment validation
  * Health check endpoints on all agents
  * Sample customer conversation end-to-end
  * Third-party API connectivity verification
- Load Testing: Azure Load Testing service (limited runs to stay in budget)
  * Target: 100 concurrent users, 1000 requests/minute
  * Monitor Azure metrics: CPU, memory, latency, errors
- Security Testing:
  * OWASP ZAP automated vulnerability scanning
  * Dependency scanning (Dependabot, Snyk)
  * Secrets scanning (git-secrets, detect-secrets)
- Disaster Recovery Testing: Quarterly full DR drill (documented in BACKUP section)

THIRD-PARTY SERVICE ACCOUNTS AND API KEYS:
Phase 1-3 Requirements (Development with Mocks):
- None required - all services mocked locally
- Optional: GitHub account for repository access (free)
- Optional: Docker Hub account for base image pulls (free tier sufficient)

Phase 4-5 Requirements (Production with Real APIs):
- Azure:
  * Azure Subscription (pay-as-you-go, $200/month budget)
  * Azure DevOps organization (free for small teams)
  * Service Principal for Terraform automation (created via Azure CLI)

- Shopify:
  * Shopify Partner Account (free) - https://www.shopify.com/partners
  * Development Store (free, created within Partner account)
  * API Credentials: API Key, API Secret, Access Token
  * Webhooks: Configure for inventory updates, order events
  * Cost: $0 (Partner program is free)

- Zendesk:
  * Zendesk Trial Account (14-day free trial) or Sandbox
  * API Token for agent authentication
  * Subdomain: {yourdomain}.zendesk.com
  * Webhooks: Configure for ticket creation/updates
  * Cost: Trial is free; ongoing use may require paid plan (~$19-49/month per agent - consider budget impact)
  * Alternative: Consider Zendesk Sandbox account (free for partners/developers)

- Mailchimp:
  * Mailchimp Free Account (up to 500 contacts, 1000 sends/month)
  * API Key for integration
  * Audience ID for subscriber list
  * Cost: $0 with free tier (upgrade if needed, starting ~$13/month)

- Google Analytics:
  * Google Account (free)
  * Google Analytics 4 Property (free)
  * Service Account for API access (created in Google Cloud Console, free)
  * Cost: $0

- OpenTelemetry (Observability):
  * Phase 1-3: Self-hosted Grafana + ClickHouse (Docker Compose, free)
  * Phase 4-5: Azure Monitor integration (included in Azure costs)

- LLM/AI Services (for agent intelligence):
  * Option 1: Azure OpenAI Service (recommended for Azure integration)
    - Requires separate Azure OpenAI access application
    - Cost: Pay-per-token (estimate $20-50/month for testing, monitor closely)
  * Option 2: OpenAI API (openai.com)
    - API Key required
    - Cost: Pay-per-token (similar pricing to Azure OpenAI)
  * Phase 1-3: Consider using mock/canned responses to avoid LLM costs during development
  * Phase 4-5: Integrate real LLM, monitor token usage closely to stay in budget

Total Estimated Ongoing Costs (Phase 4-5):
- Azure: $200/month (budget ceiling)
- Zendesk: $0-49/month (use trial/sandbox or budget for one agent license)
- Others: $0 (all free tiers)
- Recommendation: If Zendesk cost is required, reduce Azure spend to $150-180 to stay within overall budget, or use alternative ticketing system with free tier

API Key Management:
- Phase 1-3: Environment variables in .env file (not committed to Git, .env.example template provided)
- Phase 4-5: Azure Key Vault for all secrets, accessed via Managed Identity
- Rotation: Document API key rotation procedures (quarterly recommended)
- Security: Never commit secrets to Git (use .gitignore, git-secrets pre-commit hook)

DELIVERABLES:
Phase 1:
- Docker Compose configuration with all infrastructure services
- Agent container skeletons with AGNTCY SDK integration
- Mock API implementations (Shopify, Zendesk, Mailchimp)
- Unit test suite with >80% coverage
- GitHub repository with README and setup instructions
- GitHub Actions CI workflow

Phase 2:
- Complete agent implementations (Intent, Knowledge, Response, Escalation, Analytics)
- Integration test suite against mock services
- Documentation: Agent communication flows, message schemas
- Performance benchmarks (local environment baseline)

Phase 3:
- End-to-end functional test suite
- Test data sets for realistic scenarios
- Performance and load testing results (local)
- Documentation: Testing guide, troubleshooting

Phase 4:
- Terraform configurations for Azure infrastructure
- Multi-language support (Canadian French, Spanish)
- Real API integrations (Shopify, Zendesk, Mailchimp)
- Azure DevOps pipeline configuration
- Cost optimization documentation and weekly cost reports
- Disaster recovery procedures and testing results

Phase 5:
- Production deployment to Azure East US
- Security scanning reports
- Load testing results (Azure environment)
- Disaster recovery validation report
- Final blog post content and code examples
- Public GitHub repository with comprehensive README

Please create Terraform configurations that implement this architecture following Azure best practices and optimized for the $200/month Phase 4-5 budget constraint.