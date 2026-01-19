# Docker Build Context Fix

## Problem

The current Dockerfiles have `COPY ../../shared` commands that fail because Docker build context is set to subdirectories (e.g., `./agents/intent_classification`), preventing access to parent directories.

## Solution

Change build context to project root and update COPY paths.

## Required Changes

### 1. Update docker-compose.yml

Change all agent build contexts from subdirectories to root:

```yaml
# BEFORE:
agent-intent-classification:
  build:
    context: ./agents/intent_classification
    dockerfile: Dockerfile

# AFTER:
agent-intent-classification:
  build:
    context: .
    dockerfile: agents/intent_classification/Dockerfile
```

### 2. Update Agent Dockerfiles

Change COPY paths to be relative to project root:

```dockerfile
# BEFORE:
COPY requirements.txt .
COPY ../../shared /app/shared
COPY agent.py .

# AFTER:
COPY agents/intent_classification/requirements.txt .
COPY shared/ /app/shared/
COPY agents/intent_classification/agent.py .
```

### 3. Apply to All Agents

Same pattern for all 5 agents:
- intent_classification
- knowledge_retrieval
- response_generation
- escalation
- analytics

## Alternative Solution (Simpler)

Keep subdirectory context but copy shared via docker-compose volumes:

```yaml
agent-intent-classification:
  build:
    context: ./agents/intent_classification
  volumes:
    - ./shared:/app/shared:ro
```

**Recommendation**: Use Solution 1 (root context) for proper containerization.
