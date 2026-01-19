# Azure Phase 1 Demo Deployment Guide

**WARNING**: This deviates from the project plan which reserves Azure for Phase 4-5.
This is a **minimal demonstration deployment** for Phase 1 evaluation only.

---

## Cost Estimate

**Monthly Cost**: ~$50-80 (much lower than Phase 4-5's $200 budget)

### Services Required:

1. **Azure Container Instances** (chat interface): ~$15-20/month
2. **Azure Static Web Apps** (web UI): Free tier
3. **Azure Cosmos DB** (conversation logs): ~$25-30/month (serverless)
4. **Azure Application Insights** (monitoring): ~$5-10/month
5. **Azure Container Registry** (images): ~$5/month

**Backend agents can stay local** - no need to deploy all 13 services for demo.

---

## Architecture for Phase 1 Demo

```
                    Internet Users
                          |
                          v
              [Azure Static Web App]
               (Chat UI - React/Vue)
                          |
                          v
         [Azure Container Instance]
          (API Gateway + Orchestrator)
                          |
                          v
              [Your Local Agents]
           (Via ngrok tunnel or VPN)
                          |
                          v
              [Cosmos DB - Serverless]
                (Chat logs, analytics)
```

### Why This Works:

1. **Web UI** in Azure (users can access)
2. **API Gateway** in Azure (routes requests)
3. **Agents stay local** (no need to deploy everything)
4. **Logs in Azure** (for evaluation metrics)

---

## Option 1: Simple Chat Web Interface

### Step 1: Create Chat UI

I can create a simple web chat interface:

**File**: `web/chat.html` (Single-page app)

```html
<!DOCTYPE html>
<html>
<head>
    <title>AGNTCY Customer Service Demo</title>
    <style>
        /* Modern chat UI */
        body { font-family: Arial, sans-serif; }
        #chat-container { max-width: 600px; margin: 50px auto; }
        #messages {
            height: 400px;
            border: 1px solid #ccc;
            overflow-y: auto;
            padding: 10px;
        }
        .message { margin: 10px 0; }
        .user { text-align: right; color: blue; }
        .agent { text-align: left; color: green; }
    </style>
</head>
<body>
    <div id="chat-container">
        <h1>Customer Service Chat (Phase 1 Demo)</h1>
        <div id="messages"></div>
        <input type="text" id="user-input" placeholder="Type your message...">
        <button onclick="sendMessage()">Send</button>
    </div>
    <script>
        const API_ENDPOINT = 'YOUR_AZURE_FUNCTION_URL';

        async function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value;

            // Display user message
            addMessage('user', message);

            // Send to backend
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            // Display agent response
            addMessage('agent', data.response);

            input.value = '';
        }

        function addMessage(sender, text) {
            const div = document.createElement('div');
            div.className = `message ${sender}`;
            div.textContent = text;
            document.getElementById('messages').appendChild(div);
        }
    </script>
</body>
</html>
```

### Step 2: Create Azure Function API

**File**: `azure-functions/ChatAPI/function_app.py`

```python
import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="chat")
def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Chat request received')

    try:
        req_body = req.get_json()
        user_message = req_body.get('message')

        # Forward to your local agents via HTTP
        # OR use simple keyword matching for demo
        response = process_message(user_message)

        # Log to Cosmos DB for analytics
        log_conversation(user_message, response)

        return func.HttpResponse(
            json.dumps({'response': response}),
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500
        )

def process_message(message):
    """
    Phase 1 demo: Use keyword matching
    Phase 2: Forward to real agents
    """
    message_lower = message.lower()

    if 'order' in message_lower or 'tracking' in message_lower:
        return "I can help you track your order. Please provide your order number."
    elif 'return' in message_lower:
        return "I can assist with returns. What would you like to return?"
    else:
        return "Thank you for contacting us. How can I assist you today?"

def log_conversation(user_msg, agent_response):
    # TODO: Log to Cosmos DB
    pass
```

### Step 3: Deploy to Azure

```bash
# Create resource group
az group create --name agntcy-phase1-demo --location eastus

# Create Static Web App (for chat UI)
az staticwebapp create \
    --name agntcy-chat-ui \
    --resource-group agntcy-phase1-demo \
    --location eastus

# Create Function App (for API)
az functionapp create \
    --name agntcy-chat-api \
    --resource-group agntcy-phase1-demo \
    --consumption-plan-location eastus \
    --runtime python \
    --runtime-version 3.12 \
    --functions-version 4

# Deploy function
cd azure-functions
func azure functionapp publish agntcy-chat-api
```

---

## Option 2: Full Azure Deployment (Higher Cost)

If you want to deploy all agents to Azure:

### Architecture:

```
Azure Static Web App (Chat UI)
    ↓
Azure API Management (Gateway)
    ↓
Azure Container Instances (13 containers):
    - NATS
    - SLIM
    - ClickHouse
    - OTLP Collector
    - Grafana
    - 4 Mock APIs
    - 5 Agents
    ↓
Azure Cosmos DB (Logs, Analytics)
```

### Terraform for Deployment:

**File**: `terraform/phase1-demo/main.tf`

```hcl
# This would be 200-300 lines of Terraform
# Deploys all containers to Azure Container Instances
# Estimated cost: $100-150/month
```

**I can create this if you want**, but it violates the project plan.

---

## Option 3: Hybrid Approach (Recommended)

**Best for Phase 1 evaluation**:

1. **Keep agents running locally** (Docker Desktop)
2. **Expose via ngrok tunnel** (free)
3. **Create simple web UI** hosted on Azure Static Web Apps (free)
4. **Log interactions** to Azure Cosmos DB (serverless, ~$25/month)

### Setup:

```bash
# 1. Start agents locally
docker-compose up -d

# 2. Expose via ngrok
ngrok http 46357  # SLIM endpoint

# 3. Update web UI with ngrok URL
# 4. Deploy web UI to Azure Static Web Apps (free)

# 5. Create Cosmos DB for logging
az cosmosdb create \
    --name agntcy-demo-logs \
    --resource-group agntcy-phase1-demo \
    --locations regionName=eastus \
    --capabilities EnableServerless
```

**Cost**: ~$25/month (just Cosmos DB for logging)

---

## Metrics Collection

To evaluate responsiveness and quality:

### 1. Add Analytics Middleware

**File**: `shared/analytics_middleware.py`

```python
import time
from datetime import datetime
from azure.cosmos import CosmosClient

class ConversationLogger:
    def __init__(self, cosmos_endpoint, cosmos_key):
        self.client = CosmosClient(cosmos_endpoint, cosmos_key)
        self.db = self.client.get_database_client("conversations")
        self.container = self.db.get_container_client("messages")

    def log_interaction(self, user_message, agent_response, metadata):
        self.container.create_item({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_message,
            "agent_response": agent_response,
            "response_time_ms": metadata.get("response_time_ms"),
            "intent": metadata.get("intent"),
            "confidence": metadata.get("confidence"),
            "satisfaction": None  # User can rate later
        })
```

### 2. Evaluation Metrics

Track these in Cosmos DB:

```json
{
  "conversation_id": "uuid",
  "messages": [
    {
      "timestamp": "2026-01-18T12:00:00Z",
      "user": "Where is my order?",
      "agent": "I can help...",
      "response_time_ms": 450,
      "intent": "order_status",
      "confidence": 0.85
    }
  ],
  "metrics": {
    "total_messages": 5,
    "avg_response_time": 500,
    "resolution_time": 120000,
    "satisfaction_score": 4.5,
    "resolved": true
  }
}
```

### 3. Query for Evaluation

```python
# Get response time stats
SELECT AVG(c.response_time_ms) as avg_response_time,
       MAX(c.response_time_ms) as max_response_time,
       MIN(c.response_time_ms) as min_response_time
FROM c
WHERE c.timestamp >= '2026-01-18'

# Get satisfaction distribution
SELECT c.satisfaction_score, COUNT(1) as count
FROM c
GROUP BY c.satisfaction_score
```

---

## My Recommendation

**Don't deploy Phase 1 to Azure yet.** Instead:

### Better Approach:

1. ✅ **Push to GitHub** (show code quality)
2. ✅ **Create demo video** (screen recording of local Docker)
3. ✅ **Write blog post** (explain architecture)
4. ⏳ **Complete Phase 2** (add real NLP/LLM)
5. ⏳ **Then deploy Phase 2+** to Azure for real user evaluation

### Why:

- Phase 1 has template responses (not impressive for users)
- Azure costs money (violates $0 Phase 1-3 budget)
- Docker Desktop demo is sufficient for technical evaluation
- Real user testing should wait for Phase 2 (actual AI)

---

## If You Insist on Azure Demo

**I can create**:

1. Simple chat web interface (React or plain HTML)
2. Azure Function API (Python)
3. Cosmos DB for logging
4. Terraform deployment scripts
5. Analytics dashboard queries

**Estimated Cost**: $50-80/month
**Setup Time**: 2-4 hours
**Value**: Limited (Phase 1 is mock implementation)

**Would you like me to proceed with creating these files?**

Or should we:
- Focus on GitHub deployment?
- Complete CI/CD pipeline first?
- Begin Phase 2 for real user testing?
