# Contributing to AGNTCY Multi-Agent Customer Service Platform

Thank you for your interest in contributing to this educational project! This guide will help you get started.

## Project Purpose

This is an **educational example project** designed to demonstrate:
- Building multi-agent AI systems with AGNTCY SDK
- Cost-effective Azure deployment strategies
- Modern DevOps practices (IaC, CI/CD, observability)
- Real-world customer service automation

## How to Contribute

### Types of Contributions Welcome

1. **Bug Fixes**
   - Fix issues in agent logic, mock APIs, or infrastructure
   - Improve error handling and edge cases
   - Correct documentation errors

2. **Educational Enhancements**
   - Add code comments explaining complex patterns
   - Create architecture diagrams
   - Write tutorials or guides
   - Add test scenarios

3. **Phase 2+ Features**
   - Real NLP integration examples
   - LLM response generation patterns
   - Multi-language support
   - Performance optimizations

4. **Cost Optimization**
   - Azure resource optimizations
   - Alternative service suggestions
   - Budget tracking improvements

### What NOT to Contribute

- Premium Azure services that exceed $200/month budget
- Features that break AGNTCY SDK integration patterns
- Security vulnerabilities or anti-patterns
- Changes that make the project less educational

## Development Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/agntcy-multi-agent-customer-service.git
cd agntcy-multi-agent-customer-service
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env
```

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 4. Make Your Changes

Follow these guidelines:

**Code Style:**
- Use `black` for Python formatting (line length 100)
- Run `flake8` for linting
- Add type hints for public APIs
- Write docstrings (Google style)

**Testing:**
- Add unit tests for new utilities/models
- Add integration tests for agent behavior
- Maintain or improve coverage (current: 46%, target: 80% for Phase 2)
- Run tests: `pytest tests/ -v`

**Documentation:**
- Update README.md if user-facing changes
- Add code comments explaining "why" not "what"
- Update PHASE1-STATUS.md for Phase 1 changes
- Keep CLAUDE.md updated for AI assistant context

**Commit Messages:**
- Use conventional commits format
- Examples:
  - `feat: add sentiment analysis to Escalation Agent`
  - `fix: correct intent classification for return requests`
  - `docs: update setup guide with Windows troubleshooting`
  - `test: add unit tests for knowledge retrieval`

### 5. Run Quality Checks

```bash
# Format code
black shared/ agents/ tests/

# Lint code
flake8 shared/ agents/ tests/

# Security scan
bandit -r shared/ agents/

# Run tests with coverage
pytest tests/ --cov=shared --cov=agents --cov-report=html
# Ensure coverage doesn't decrease

# Build Docker images (validate)
docker-compose build
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what and why
- Screenshots if UI/visual changes
- Test results
- Checklist of completed items

## Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows project style (black, flake8 pass)
- [ ] Tests added/updated and passing
- [ ] Coverage maintained or improved
- [ ] Documentation updated
- [ ] Commits follow conventional format
- [ ] No secrets or API keys in code
- [ ] Changes align with educational goals
- [ ] Budget constraints respected ($200/month for Phase 4-5)

## Code Review Process

1. Maintainers will review within 1-2 weeks
2. Address feedback and update PR
3. Once approved, maintainer will merge
4. Your contribution will be acknowledged in release notes

## Project Structure

```
project-root/
├── agents/              # Agent implementations
├── mocks/              # Mock API services
├── shared/             # Shared utilities
├── tests/              # Test suites
├── config/             # Service configurations
├── terraform/          # Infrastructure as Code
└── docs/               # Documentation
```

## Coding Standards

### Python

```python
# Good: Clear, documented, tested
def classify_intent_mock(self, message_text: str) -> tuple:
    """
    Classify customer intent using keyword matching.

    Phase 1 implementation uses simple rules.
    Phase 2 will integrate real NLP (Azure Language Service).

    Args:
        message_text: Customer message content

    Returns:
        Tuple of (intent, confidence, extracted_entities)
    """
    message_lower = message_text.lower()

    if any(word in message_lower for word in ["order", "tracking"]):
        return Intent.ORDER_STATUS, 0.85, {}

    return Intent.GENERAL_INQUIRY, 0.50, {}
```

### Docker

```dockerfile
# Good: Multi-stage, minimal, documented
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY ../../shared /app/shared

# Copy agent code
COPY agent.py .

# Health check
HEALTHCHECK --interval=30s CMD python -c "print('healthy')"

# Run agent
CMD ["python", "agent.py"]
```

## Testing Guidelines

### Unit Tests (tests/unit/)

Test individual functions and classes:

```python
def test_intent_classification_order_status():
    """Test keyword matching for order status intent."""
    agent = IntentClassificationAgent()
    intent, confidence, entities = agent._classify_intent_mock(
        "Where is my order #12345?"
    )

    assert intent == Intent.ORDER_STATUS
    assert confidence > 0.8
    assert "order_number" in entities
```

### Integration Tests (tests/integration/)

Test agent message flows:

```python
@pytest.mark.asyncio
async def test_agent_handles_customer_message(sample_a2a_message):
    """Test agent processes A2A message correctly."""
    agent = IntentClassificationAgent()
    result = await agent.handle_message(sample_a2a_message)

    content = extract_message_content(result)
    assert content["intent"] in Intent.__members__.values()
    assert 0 <= content["confidence"] <= 1.0
```

## Questions?

- Open a GitHub Discussion for general questions
- Open an Issue for bugs or feature requests
- Check CLAUDE.md for AI assistant guidance
- Review PROJECT-README.txt for full specifications

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for helping make this educational project better!** 🎓
