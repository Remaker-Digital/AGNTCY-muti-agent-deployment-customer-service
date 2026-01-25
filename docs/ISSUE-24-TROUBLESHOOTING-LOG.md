# Issue #24 Implementation - Troubleshooting Log

**Issue:** Customer Order Status Inquiries
**Implementation Date:** 2026-01-23
**Status:** ✅ Resolved - All tests passing

---

## Issues Encountered and Solutions

### Issue 1: Pytest Async Fixture Generators

**Problem:**
```
AttributeError: 'async_generator' object has no attribute 'handle_message'
```

**Root Cause:**
- Using `async def` for pytest fixtures returns async generator objects, not the actual agent instances
- Tests tried to call methods on generators instead of agent objects

**Solution:**
- Changed fixtures from `async def` to regular `def`
- Moved async agent initialization (`await agent.initialize()`) into test methods
- Pattern:
  ```python
  @pytest.fixture(scope="function")
  def intent_agent(self):
      agent = IntentClassificationAgent()
      yield agent
      agent.cleanup()

  async def test_something(self, intent_agent):
      await intent_agent.initialize()  # Do async init in test
      # ... test code
  ```

**Reference:** https://docs.pytest.org/en/stable/fixture.html

**Future Prevention:**
- Always use synchronous fixtures with manual async initialization for agent tests
- Avoid `@pytest.fixture` with `async def` for objects that need method calls

---

### Issue 2: Intent Classification Keyword Gaps

**Problem:**
- Query "What's the status of order #99999?" classified as `GENERAL_INQUIRY` instead of `ORDER_STATUS`
- Confidence score too low for order status queries

**Root Cause:**
- Keyword list didn't include common phrases like:
  - "status of order"
  - "status of my order"
  - "been delivered"

**Solution:**
- Enhanced keyword matching list in `agents/intent_classification/agent.py:214-217`:
  ```python
  if any(word in message_lower for word in [
      "where is my order", "track", "tracking", "shipment", "delivery",
      "shipped", "arrive", "status of order", "status of my order",
      "order status", "been delivered", "my order"
  ]):
  ```

**Future Prevention:**
- When adding new intents, test with multiple phrase variations
- Consider creating test fixtures with diverse customer query patterns
- Maintain keyword list in separate config for easier updates

---

### Issue 3: Docker vs Test Environment Hostname Mismatch

**Problem:**
```
httpx.ConnectError: [Errno 11001] getaddrinfo failed
```

**Root Cause:**
- Knowledge Retrieval Agent configured to use Docker Compose hostname `mock-shopify:8000`
- Integration tests run outside Docker, need `localhost:8001`
- DNS resolution fails for `mock-shopify` when running tests locally

**Solution:**
- Added test fixture override in `tests/integration/test_order_status_flow.py:110-113`:
  ```python
  @pytest.fixture(scope="function")
  def knowledge_agent(self):
      agent = KnowledgeRetrievalAgent()
      # Override for testing outside Docker
      agent.shopify_client.base_url = "http://localhost:8001"
      agent.logger.info(f"Test override: Using Shopify URL {agent.shopify_client.base_url}")
      yield agent
      agent.cleanup()
  ```

**Future Prevention:**
- Always provide test fixtures with environment-specific overrides
- Consider using environment variables for service URLs (e.g., `SHOPIFY_URL`)
- Document hostname differences between Docker Compose and local testing

---

### Issue 4: Stale Docker Container Code

**Problem:**
- Mock Shopify API endpoint `/admin/api/2024-01/orders/10234.json` returned 404
- Order exists in test data but container had outdated code
- List endpoint worked, but single order endpoint failed

**Root Cause:**
- Docker image was built from old version of `mocks/shopify/app.py`
- Old code had incorrect order matching logic (checking `order.get("id")` with `int` type)
- Docker build cache prevented fresh build

**Solution:**
1. Identified stale container by testing API directly:
   ```bash
   curl http://localhost:8001/admin/api/2024-01/orders.json  # ✅ Works
   curl http://localhost:8001/admin/api/2024-01/orders/10234.json  # ❌ 404
   ```
2. Verified test data exists: `test-data/shopify/orders.json` contains order 10234
3. Rebuilt container with `--no-cache`:
   ```bash
   docker-compose build --no-cache mock-shopify
   docker-compose up -d mock-shopify
   ```

**Future Prevention:**
- Always rebuild containers with `--no-cache` when fixing API bugs
- Add health check endpoints that validate data loading
- Consider container versioning (e.g., `mock-shopify:v1.0.1`) to force rebuilds

---

### Issue 5: Docker Build Context Path Mismatch

**Problem:**
```
failed to solve: "/mocks/shopify/app.py": not found
```

**Root Cause:**
- `docker-compose.yml` sets build context to `./mocks/shopify`
- Dockerfile COPY commands expected project root context:
  ```dockerfile
  COPY mocks/shopify/requirements.txt .  # ❌ Wrong
  COPY mocks/shopify/app.py .            # ❌ Wrong
  ```
- When build context is `./mocks/shopify`, files are already at context root

**Solution:**
- Updated `mocks/shopify/Dockerfile` COPY paths:
  ```dockerfile
  # Build context is ./mocks/shopify so files are at root
  COPY requirements.txt .  # ✅ Correct
  COPY app.py .            # ✅ Correct
  ```

**Reference:** Docker build context - https://docs.docker.com/build/building/context/

**Future Prevention:**
- Always check `docker-compose.yml` build context before writing Dockerfile COPY paths
- Add comments in Dockerfile documenting expected build context
- Test Docker builds locally before committing changes

---

### Issue 6: Async Cleanup Runtime Warnings

**Problem:**
```
RuntimeWarning: coroutine 'KnowledgeRetrievalAgent.cleanup_async' was never awaited
```

**Root Cause:**
- `cleanup()` method tried to create async task with `asyncio.create_task()`
- When tests finish, event loop is already closed
- Creating task on closed loop raises `RuntimeError`

**Solution:**
- Added event loop check in `agents/knowledge_retrieval/agent.py:660-674`:
  ```python
  def cleanup(self):
      try:
          try:
              loop = asyncio.get_running_loop()
              loop.create_task(self.cleanup_async())
          except RuntimeError:
              # No event loop running - skip async cleanup
              self.logger.debug("No event loop running, skipping async cleanup")
      except Exception as e:
          self.logger.error(f"Error during cleanup: {e}")
  ```

**Future Prevention:**
- Always check for running event loop before creating async tasks
- Provide synchronous cleanup fallback for when loop is unavailable
- Consider using `asyncio.run()` for cleanup if event loop needed

---

### Issue 7: Windows Unicode Encoding in Test Output

**Problem:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0: character maps to <undefined>
```

**Root Cause:**
- Test print statements used Unicode checkmark character `✓` (U+2713)
- Windows console (cp1252 encoding) cannot display this character
- Python default encoding on Windows doesn't support full Unicode

**Solution:**
- Replaced all `✓` with `[OK]` in test output:
  ```python
  # Before
  print(f"✓ Step 1 Complete: Intent classified")

  # After
  print(f"[OK] Step 1 Complete: Intent classified")
  ```

**Files Modified:**
- `tests/integration/test_order_status_flow.py:195, 234, 270, 338, 411, 443`

**Future Prevention:**
- Avoid Unicode symbols in test output (use ASCII alternatives)
- Consider using `sys.stdout.reconfigure(encoding='utf-8')` for Windows UTF-8 support
- Or use environment variable `PYTHONIOENCODING=utf-8` for full Unicode

**Reference:** https://docs.python.org/3/library/sys.html#sys.stdout

---

## Summary Statistics

**Total Issues:** 7
**Resolution Time:** ~45 minutes
**Test Success Rate:** 3/3 tests passing (100%)

### Issue Categories:
- **Testing Infrastructure:** 3 issues (async fixtures, hostname mismatch, Unicode encoding)
- **Docker/Container:** 2 issues (stale code, build context)
- **Business Logic:** 1 issue (keyword gaps)
- **Cleanup/Lifecycle:** 1 issue (async cleanup warnings)

### Most Time-Consuming Issues:
1. **Stale Docker Container** (~15 min) - Required debugging API, checking data, rebuilding
2. **Docker Build Context** (~10 min) - Required understanding Dockerfile/docker-compose interaction
3. **Async Fixtures** (~10 min) - Required understanding pytest async behavior

### Quick Fixes:
1. **Unicode Encoding** (~2 min) - Simple search/replace
2. **Intent Keywords** (~3 min) - Add missing phrases
3. **Hostname Override** (~5 min) - Add test fixture override

---

## Key Learnings

### 1. Docker Build Best Practices
- **Always verify build context** in `docker-compose.yml` before writing Dockerfile paths
- **Use `--no-cache`** when debugging container issues to eliminate cache as variable
- **Test API endpoints directly** with curl before blaming application code

### 2. Pytest Async Patterns
- **Avoid async fixtures** for objects needing method calls
- **Initialize async agents in test methods**, not fixtures
- **Use synchronous fixtures** with `yield` for setup/teardown

### 3. Windows Development Considerations
- **Avoid Unicode symbols** in console output (use ASCII alternatives)
- **Test on target platform** if developing cross-platform
- **Set PYTHONIOENCODING=utf-8** for full Unicode support on Windows

### 4. Multi-Environment Testing
- **Provide environment-specific overrides** in test fixtures
- **Document hostname/URL differences** between environments
- **Use environment variables** for configuration that varies by environment

### 5. Intent Classification Tuning
- **Test with diverse phrasings** when adding intents
- **Maintain keyword lists separately** from code for easier updates
- **Consider phrase variations** customers actually use

---

## Future Improvements

### Short-Term (Phase 2)
1. Extract intent keywords to configuration file for easier maintenance
2. Add environment variable support for service URLs (Shopify, Zendesk, etc.)
3. Create health check endpoint for mock APIs to validate data loading
4. Add pytest markers for Docker-dependent tests (`@pytest.mark.docker`)

### Medium-Term (Phase 3)
1. Implement proper NLP-based intent classification (replace keyword matching)
2. Add test coverage for all intent classification edge cases
3. Create automated Docker rebuild script when test data changes
4. Add integration test for cross-environment compatibility

### Long-Term (Phase 4-5)
1. Replace mock APIs with real Shopify/Zendesk integration
2. Implement proper Windows UTF-8 support in test runners
3. Add performance benchmarking for all agent response times
4. Create automated regression suite for all 50 Phase 2 user stories

---

**Document Owner:** Claude Sonnet 4.5 (AI Assistant)
**Last Updated:** 2026-01-23
**Related Issues:** #24 (Customer Order Status Inquiries)
**Related Files:**
- `tests/integration/test_order_status_flow.py`
- `agents/intent_classification/agent.py`
- `agents/knowledge_retrieval/agent.py`
- `mocks/shopify/Dockerfile`
- `mocks/shopify/app.py`
