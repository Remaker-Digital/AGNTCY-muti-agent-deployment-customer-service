# User Stories - AGNTCY Multi-Agent Customer Service Platform

**Organization**: Phased by PROJECT-README.txt timeline
**Format**: Epic-level themes with example scenarios
**Terminology**: Concrete (Shopify products, Zendesk tickets, Mailchimp campaigns)
**Total Stories**: 130 across 7 actor personas

---

## Epic Structure (7 Actors)

### Epic 1: Customer Stories (40 stories)
**Actor**: Customer - Past purchaser with order history in Shopify
**Channels**: Web chat, email, Mailchimp notifications
**Integration Points**: Shopify orders, Zendesk tickets

### Epic 2: Prospect Stories (25 stories)
**Actor**: Prospect - Visitor with no purchase history
**Channels**: Web chat, email opt-in
**Integration Points**: Shopify product catalog, Mailchimp subscriber lists

### Epic 3: Support Agent Stories (15 stories)
**Actor**: Support - Human Zendesk agent handling escalated cases
**Channels**: Zendesk ticket interface
**Integration Points**: Escalation from AI to human via Zendesk API

### Epic 4: Service Agent Stories (15 stories)
**Actor**: Service - Human specialist for repairs/upgrades
**Channels**: Zendesk ticket interface (service queue)
**Integration Points**: Shopify order history, service request routing

### Epic 5: Sales Agent Stories (15 stories)
**Actor**: Sales - Human sales team member for high-value leads
**Channels**: Zendesk ticket interface (sales queue)
**Integration Points**: Lead scoring, conversion tracking via Google Analytics

### Epic 6: AI Customer Assistant Stories (5 stories)
**Actor**: AI Agent - Proactive engagement system
**Channels**: Web chat (initiated by system)
**Integration Points**: Google Analytics behavior tracking, Shopify browsing data

### Epic 7: Operator Stories (15 stories)
**Actor**: Operator - DevOps/Platform administrator
**Channels**: Azure Portal, GitHub, monitoring dashboards
**Integration Points**: Azure resources, CI/CD pipelines, observability stack

---

## Phase 1: Infrastructure & Containers ($0 budget)
**Focus**: Docker Compose, mock APIs, agent skeletons, local testing
**Stories**: 15 foundational stories

### EPIC 1: Customer Stories - Phase 1 (3 stories)

#### Story 1.1: Mock Customer Order Status Inquiry
**Theme**: Basic customer inquiry handling
**Example Scenarios**:
- Customer asks "Where is my order?" via mock web chat interface
- System queries mock Shopify API for order #12345
- Response generated with tracking info from test fixtures
**Technical Scope**: Mock Shopify API, basic Intent Classification, canned responses
**Acceptance Criteria**: Mock conversation flow completes end-to-end in local Docker environment

#### Story 1.2: Mock Customer Product Question
**Theme**: Product information retrieval
**Example Scenarios**:
- Customer asks "Is the organic mango soap in stock?"
- System queries mock Shopify product catalog
- Response includes availability, price, description from test data
**Technical Scope**: Mock Shopify product endpoints, Knowledge Retrieval agent skeleton
**Acceptance Criteria**: Product data retrieved and formatted in response

#### Story 1.3: Mock Customer Escalation Flow
**Theme**: AI-to-human handoff
**Example Scenarios**:
- Customer reports "My package says delivered but I never received it"
- System detects escalation trigger words
- Mock Zendesk ticket created with conversation context
**Technical Scope**: Escalation agent logic, mock Zendesk API
**Acceptance Criteria**: Ticket created in mock Zendesk with correct priority/tags

---

### EPIC 2: Prospect Stories - Phase 1 (2 stories)

#### Story 2.1: Mock Prospect Product Inquiry
**Theme**: Anonymous user product questions
**Example Scenarios**:
- Prospect asks "What ingredients are in the lavender soap?"
- System retrieves product details from mock Shopify catalog
- Response provided without requiring login
**Technical Scope**: Product data retrieval for unauthenticated users
**Acceptance Criteria**: Response generated without customer identification

#### Story 2.2: Mock Prospect Email Capture
**Theme**: Lead generation via email opt-in
**Example Scenarios**:
- Prospect asks to be notified when eucalyptus soap is back in stock
- System prompts for email address
- Mock Mailchimp subscriber created with product interest tag
**Technical Scope**: Mock Mailchimp API, subscriber creation
**Acceptance Criteria**: Email stored in mock Mailchimp with proper tags

---

### EPIC 3: Support Agent Stories - Phase 1 (2 stories)

#### Story 3.1: Mock Support Ticket Creation
**Theme**: Escalation creates properly formatted tickets
**Example Scenarios**:
- Customer issue escalated from AI chat
- Mock Zendesk ticket includes: conversation transcript, customer email, issue summary
- Ticket assigned to "support" queue
**Technical Scope**: Zendesk ticket creation API, context serialization
**Acceptance Criteria**: All required fields populated in mock ticket

#### Story 3.2: Mock Support Ticket Notification
**Theme**: Support agent receives escalation notification
**Example Scenarios**:
- New ticket created in mock Zendesk
- System logs notification event (email would be sent in production)
- Ticket appears in support queue
**Technical Scope**: Webhook simulation, queue management
**Acceptance Criteria**: Notification logged with correct recipient and content

---

### EPIC 4: Service Agent Stories - Phase 1 (1 story)

#### Story 4.1: Mock Service Request Routing
**Theme**: Service-specific escalations separated from support
**Example Scenarios**:
- Customer asks "How do I arrange repair for my soap dispenser?"
- System routes to service queue (not general support)
- Mock Zendesk ticket created with "service" tag
**Technical Scope**: Intent classification for service vs support, routing logic
**Acceptance Criteria**: Service requests tagged and routed correctly

---

### EPIC 5: Sales Agent Stories - Phase 1 (1 story)

#### Story 5.1: Mock Sales Lead Scoring
**Theme**: High-value prospects flagged for sales follow-up
**Example Scenarios**:
- Prospect inquires about bulk order pricing for 500 units
- System detects high-value opportunity keywords
- Mock Zendesk ticket created for sales team with "lead" tag
**Technical Scope**: Keyword detection, sales routing logic
**Acceptance Criteria**: High-value leads routed to sales queue

---

### EPIC 6: AI Customer Assistant Stories - Phase 1 (1 story)

#### Story 6.1: Mock Proactive Engagement Trigger
**Theme**: AI initiates conversation based on behavior
**Example Scenarios**:
- Mock Google Analytics event: customer viewed 5 products in 10 minutes
- System simulates proactive chat offer: "Can I help you find something?"
- Customer can accept or dismiss
**Technical Scope**: Event trigger simulation, proactive message generation
**Acceptance Criteria**: Trigger logic executes, message queued for delivery

---

### EPIC 7: Operator Stories - Phase 1 (5 stories)

#### Story 7.1: Operator Starts Local Environment
**Theme**: Developer experience for local setup
**Example Scenarios**:
- Operator runs `docker-compose up`
- All 13 services start successfully
- Health checks pass, observability dashboard accessible
**Technical Scope**: Docker Compose orchestration, health checks
**Acceptance Criteria**: Clean startup with no errors, all services healthy

#### Story 7.2: Operator Views Agent Metrics
**Theme**: Observability during development
**Example Scenarios**:
- Operator opens Grafana at localhost:3001
- Dashboard shows: agent response times, message counts, error rates
- Traces visible in ClickHouse for debugging
**Technical Scope**: Grafana dashboards, OTLP telemetry, ClickHouse queries
**Acceptance Criteria**: All agents reporting telemetry, dashboard displays real-time data

#### Story 7.3: Operator Runs Test Suite
**Theme**: Automated testing for validation
**Example Scenarios**:
- Operator runs `pytest tests/`
- All unit tests pass (>80% coverage target)
- Test report generated with coverage metrics
**Technical Scope**: Pytest configuration, test fixtures, coverage reporting
**Acceptance Criteria**: Test suite executes, coverage meets threshold

#### Story 7.4: Operator Inspects Mock API Responses
**Theme**: Debugging with test fixtures
**Example Scenarios**:
- Operator accesses mock Shopify API directly: `curl localhost:8001/products`
- Test data returned matches fixtures in test-data/shopify/
- Operator modifies fixtures to test edge cases
**Technical Scope**: Direct API access, fixture management, documentation
**Acceptance Criteria**: All mock endpoints documented and accessible

#### Story 7.5: Operator Reviews Agent Logs
**Theme**: Troubleshooting agent behavior
**Example Scenarios**:
- Agent fails to route message correctly
- Operator checks Docker logs: `docker-compose logs intent-classifier`
- Error message clearly indicates issue (e.g., "Unknown intent: refund_request")
**Technical Scope**: Structured logging, log aggregation, error messages
**Acceptance Criteria**: Logs provide actionable troubleshooting information

---

## Phase 2: Business Logic Implementation ($0 budget)
**Focus**: Agent intelligence, conversation flows, integration with mocks
**Stories**: 50 stories (30 Customer, 10 Prospect, 5 Support, 2 Service, 2 Sales, 1 AI Assistant)

### EPIC 1: Customer Stories - Phase 2 (30 stories)

#### Story 1.4: Order Status with Tracking Details
**Theme**: Enhanced order inquiry with Shopify integration
**Example Scenarios**:
- Customer: "Where is order #10234?"
- System retrieves from mock Shopify: status, tracking number, carrier, ETA
- Response: "Your order is in transit with USPS. Tracking: 9400123456789. Expected delivery: Jan 25."

#### Story 1.5: Order Modification Request
**Theme**: Customer wants to change order before shipment
**Example Scenarios**:
- Customer: "Can I change my shipping address for order #10234?"
- System checks order status (if not shipped, provide instructions; if shipped, escalate)
- Mock Shopify order update or Zendesk escalation

#### Story 1.6: Return/Refund Inquiry
**Theme**: Post-purchase issue resolution
**Example Scenarios**:
- Customer: "I want to return the lavender soap, it irritates my skin"
- System retrieves return policy from knowledge base
- Provides return instructions or escalates if complex

#### Story 1.7: Product Recommendation Based on Purchase History
**Theme**: Personalized suggestions
**Example Scenarios**:
- Customer: "What else would go well with the mango soap I bought?"
- System analyzes past purchases (mocked customer data)
- Suggests complementary products: "Many customers also enjoy our mango body lotion"

#### Story 1.8: Reorder Previous Purchase
**Theme**: Quick repurchase flow
**Example Scenarios**:
- Customer: "I want to reorder what I bought last month"
- System retrieves order history from mock Shopify
- Generates cart link with previous items

#### Story 1.9: Delivery Issue - Not Received
**Theme**: Escalation for lost packages
**Example Scenarios**:
- Customer: "My order says delivered but I didn't receive it"
- System escalates immediately (high priority)
- Mock Zendesk ticket created with customer details, order info, tracking

#### Story 1.10: Product Quality Complaint
**Theme**: Defective or incorrect product
**Example Scenarios**:
- Customer: "The soap I received is a different scent than I ordered"
- System gathers: order number, product received, product expected
- Escalates to support with replacement/refund options

#### Story 1.11: Subscription Management
**Theme**: Modify recurring order (if applicable)
**Example Scenarios**:
- Customer: "I want to pause my monthly soap subscription"
- System checks subscription status in mock Shopify
- Provides pause/cancel options or escalates for changes

#### Story 1.12: Gift Order Inquiry
**Theme**: Gift-related questions
**Example Scenarios**:
- Customer: "Can I send this as a gift with a custom message?"
- System retrieves gift options from Shopify product settings
- Explains gift wrapping, messages, separate shipping

#### Story 1.13: Bulk Purchase Discount
**Theme**: Pricing for large quantities
**Example Scenarios**:
- Customer: "Do you offer discounts for orders over 50 units?"
- System provides tiered pricing if configured
- If not available, escalates to sales

#### Story 1.14: Loyalty Program Inquiry
**Theme**: Rewards or points questions
**Example Scenarios**:
- Customer: "How many points do I have?"
- System retrieves loyalty data (mocked)
- Explains points balance and redemption options

#### Story 1.15: Shipping Cost Question
**Theme**: Delivery pricing inquiry
**Example Scenarios**:
- Customer: "How much is shipping to Canada?"
- System retrieves shipping rates from Shopify settings
- Provides rates by carrier and delivery speed

#### Story 1.16: Order Cancellation Request
**Theme**: Cancel before shipment
**Example Scenarios**:
- Customer: "Cancel my order #10234"
- System checks order status in mock Shopify
- If not shipped, confirms cancellation; if shipped, explains return process

#### Story 1.17: Promo Code Application
**Theme**: Discount code assistance
**Example Scenarios**:
- Customer: "I have a code SAVE10 but it's not working"
- System validates code against mock Shopify discounts
- Explains expiration, eligibility, or applies code

#### Story 1.18: Product Comparison
**Theme**: Help choosing between options
**Example Scenarios**:
- Customer: "What's the difference between lavender and eucalyptus soap?"
- System retrieves product details for both
- Compares ingredients, benefits, customer reviews

#### Story 1.19: Allergy/Ingredient Concern
**Theme**: Safety and suitability questions
**Example Scenarios**:
- Customer: "I'm allergic to coconut oil. Which soaps are safe for me?"
- System filters products by ingredient
- Lists safe options or recommends consulting ingredients list

#### Story 1.20: International Shipping Inquiry
**Theme**: Cross-border delivery questions
**Example Scenarios**:
- Customer: "Do you ship to the UK?"
- System checks shipping zones in Shopify settings
- Provides international rates, delivery times, customs info

#### Story 1.21: Payment Method Issue
**Theme**: Checkout or payment problems
**Example Scenarios**:
- Customer: "My credit card was declined"
- System provides troubleshooting steps
- Suggests alternative payment methods or escalates if persistent

#### Story 1.22: Order History Review
**Theme**: Past purchase lookup
**Example Scenarios**:
- Customer: "What did I order in December?"
- System retrieves order history from mock Shopify
- Lists orders with dates, products, totals

#### Story 1.23: Wholesale Inquiry
**Theme**: Business/wholesale pricing
**Example Scenarios**:
- Customer: "I own a spa. Do you have wholesale pricing?"
- System provides wholesale application info
- Escalates to sales for follow-up

#### Story 1.24: Backorder Status
**Theme**: Out-of-stock product inquiry
**Example Scenarios**:
- Customer: "When will the mango soap be back in stock?"
- System checks inventory in mock Shopify
- Provides ETA or offers notification signup

#### Story 1.25: Email Preference Management
**Theme**: Unsubscribe or modify marketing emails
**Example Scenarios**:
- Customer: "I'm getting too many emails"
- System provides Mailchimp unsubscribe link
- Offers to reduce frequency vs full unsubscribe

#### Story 1.26: Account Login Issue
**Theme**: Password reset or account access
**Example Scenarios**:
- Customer: "I forgot my password"
- System provides Shopify password reset link
- Escalates if account locked or suspicious activity

#### Story 1.27: Gift Card Balance
**Theme**: Check gift card value
**Example Scenarios**:
- Customer: "How much is left on my gift card?"
- System queries Shopify gift card API (mocked)
- Provides balance and expiration date

#### Story 1.28: Store Location/Hours Inquiry
**Theme**: Physical store information (if applicable)
**Example Scenarios**:
- Customer: "Do you have a physical store I can visit?"
- System retrieves store info from knowledge base
- Provides address, hours, or explains online-only

#### Story 1.29: Corporate/Bulk Order
**Theme**: Large quantity for events/gifts
**Example Scenarios**:
- Customer: "I need 200 soaps for a wedding favor"
- System detects high quantity
- Escalates to sales for custom pricing and logistics

#### Story 1.30: Sustainability/Ethical Sourcing
**Theme**: Company values and product sourcing
**Example Scenarios**:
- Customer: "Are your soaps cruelty-free?"
- System retrieves company policy from knowledge base
- Provides certifications, ingredient sourcing details

#### Story 1.31: Special Occasion Deadline
**Theme**: Rush delivery for events
**Example Scenarios**:
- Customer: "I need this by Friday for a birthday"
- System calculates delivery time from Shopify shipping settings
- Suggests expedited shipping or escalates if tight timeline

#### Story 1.32: Product Customization Request
**Theme**: Personalization options
**Example Scenarios**:
- Customer: "Can I get custom labels for a corporate gift?"
- System checks if customization available
- Explains options or escalates for custom orders

#### Story 1.33: Warranty/Guarantee Question
**Theme**: Product satisfaction policies
**Example Scenarios**:
- Customer: "What's your satisfaction guarantee?"
- System retrieves return/refund policy from knowledge base
- Explains timeframes, conditions, process

---

### EPIC 2: Prospect Stories - Phase 2 (10 stories)

#### Story 2.3: Prospect Product Discovery
**Theme**: Browsing assistance for anonymous users
**Example Scenarios**:
- Prospect: "What types of soap do you sell?"
- System lists product categories from Shopify catalog
- Provides top sellers or seasonal items

#### Story 2.4: Prospect Ingredient Question
**Theme**: Product details for research
**Example Scenarios**:
- Prospect: "What ingredients are in the eucalyptus soap?"
- System retrieves product details from Shopify
- Lists ingredients, benefits, usage instructions

#### Story 2.5: Prospect Price Comparison
**Theme**: Value proposition explanation
**Example Scenarios**:
- Prospect: "Why is this soap $12 when drugstore soap is $3?"
- System explains: organic ingredients, handmade, sustainability
- Links to about/values page

#### Story 2.6: Prospect Email List Signup
**Theme**: Lead capture for marketing
**Example Scenarios**:
- Prospect: "I'd like to get sale notifications"
- System prompts for email
- Creates Mailchimp subscriber with "sales_interest" tag

#### Story 2.7: Prospect Out-of-Stock Notification
**Theme**: Waitlist for unavailable products
**Example Scenarios**:
- Prospect: "The rose soap is sold out. Can you notify me when it's back?"
- System captures email and product interest
- Creates Mailchimp subscriber with product-specific tag

#### Story 2.8: Prospect First-Time Buyer Discount
**Theme**: Conversion incentive
**Example Scenarios**:
- Prospect: "Do you have any discounts for new customers?"
- System provides first-order promo code
- Explains terms and expiration

#### Story 2.9: Prospect Shipping Policy Question
**Theme**: Pre-purchase logistics inquiry
**Example Scenarios**:
- Prospect: "How long does shipping take?"
- System retrieves shipping policy from knowledge base
- Explains delivery times by region

#### Story 2.10: Prospect Return Policy Question
**Theme**: Risk mitigation for new buyers
**Example Scenarios**:
- Prospect: "What if I don't like it?"
- System explains return/refund policy
- Emphasizes satisfaction guarantee to build confidence

#### Story 2.11: Prospect Gift Suggestion
**Theme**: Shopping assistance for gift buyers
**Example Scenarios**:
- Prospect: "I'm looking for a gift for someone who loves lavender"
- System suggests lavender-scented products
- Offers gift wrapping and message options

#### Story 2.12: Prospect Sample Request
**Theme**: Trial before commitment
**Example Scenarios**:
- Prospect: "Do you sell sample sizes?"
- System checks for sample/trial products in Shopify
- Explains options or suggests starter sets

---

### EPIC 3: Support Agent Stories - Phase 2 (5 stories)

#### Story 3.3: Support Reviews Escalated Ticket
**Theme**: Human agent receives AI-escalated case
**Example Scenarios**:
- Support opens Zendesk ticket created by AI
- Ticket includes: full conversation transcript, customer order history, AI's reason for escalation
- Support picks up conversation seamlessly

#### Story 3.4: Support Requests Additional Context
**Theme**: Agent needs more info from AI system
**Example Scenarios**:
- Support reviews ticket but needs clarification
- Support queries AI system: "What was customer's exact complaint?"
- AI provides additional context from conversation logs

#### Story 3.5: Support Resolves and Closes Ticket
**Theme**: Case resolution workflow
**Example Scenarios**:
- Support resolves customer issue (refund processed, replacement sent)
- Support closes Zendesk ticket with resolution notes
- Customer receives closure notification via Mailchimp

#### Story 3.6: Support Escalates to Management
**Theme**: Complex cases requiring supervisor
**Example Scenarios**:
- Customer demands refund outside policy
- Support escalates within Zendesk to manager queue
- Manager receives case with support's notes and recommendation

#### Story 3.7: Support Updates Knowledge Base
**Theme**: Continuous improvement feedback loop
**Example Scenarios**:
- Support notices AI repeatedly escalates a question type
- Support adds answer to knowledge base
- AI system updated with new response capability (future iteration)

---

### EPIC 4: Service Agent Stories - Phase 2 (2 stories)

#### Story 4.2: Service Receives Repair Request
**Theme**: Product service case handling
**Example Scenarios**:
- Service opens Zendesk ticket: customer's soap dispenser pump broke
- Ticket includes: purchase date, product SKU, customer address
- Service initiates warranty replacement process

#### Story 4.3: Service Coordinates Upgrade
**Theme**: Product upgrade or exchange
**Example Scenarios**:
- Customer wants to upgrade subscription from monthly to quarterly
- Service reviews account in Shopify
- Processes upgrade and confirms with customer

---

### EPIC 5: Sales Agent Stories - Phase 2 (2 stories)

#### Story 5.2: Sales Receives High-Value Lead
**Theme**: Qualified prospect handoff
**Example Scenarios**:
- Sales opens Zendesk ticket: prospect inquired about 500-unit bulk order
- Ticket includes: conversation log, product interest, contact info
- Sales reaches out with custom quote

#### Story 5.3: Sales Converts Lead
**Theme**: Closing opportunity
**Example Scenarios**:
- Sales negotiates pricing and terms with bulk order lead
- Sales creates custom Shopify invoice or discount code
- Opportunity tracked in Google Analytics (mocked)

---

### EPIC 6: AI Customer Assistant Stories - Phase 2 (1 story)

#### Story 6.2: AI Proactively Suggests Cart Recovery
**Theme**: Abandoned cart re-engagement
**Example Scenarios**:
- Google Analytics (mocked) detects: customer added items to cart, left site
- AI initiates chat (or email via Mailchimp): "Still interested in the mango soap?"
- Customer returns and completes purchase

---

### EPIC 7: Operator Stories - Phase 2 (0 additional stories for Phase 2)
*Operator stories in Phase 2 primarily involve monitoring agent logic execution, covered by Phase 1 stories*

---

## Phase 3: Testing & Validation ($0 budget)
**Focus**: Functional testing, performance benchmarking, conversation quality
**Stories**: 20 stories (5 Customer, 5 Prospect, 3 Support, 2 Service, 2 Sales, 1 AI Assistant, 2 Operator)

### EPIC 1: Customer Stories - Phase 3 (5 stories)

#### Story 1.34: Validate End-to-End Order Status Flow
**Theme**: Integration test for common path
**Example Scenarios**:
- Test script simulates: customer asks order status → AI queries Shopify → response delivered
- Verify: response time <2s, accuracy 100%, no errors

#### Story 1.35: Validate Escalation Accuracy
**Theme**: Ensure appropriate cases escalate
**Example Scenarios**:
- Test suite runs 100 scenarios: 30 should escalate, 70 should not
- Verify: escalation precision >90%, recall >95%

#### Story 1.36: Validate Multi-Turn Conversations
**Theme**: Context retention across messages
**Example Scenarios**:
- Customer: "What's the status of my order?"
- AI: "Which order? You have two recent orders."
- Customer: "The one from last week"
- Verify: AI correctly identifies order #10234 from context

#### Story 1.37: Validate Error Handling
**Theme**: Graceful degradation when services fail
**Example Scenarios**:
- Mock Shopify API returns 500 error
- Verify: AI responds with "I'm having trouble accessing order info. Let me escalate you to support."

#### Story 1.38: Load Test Customer Conversation Capacity
**Theme**: Performance under concurrent load
**Example Scenarios**:
- Locust test: 50 concurrent customer conversations
- Verify: response time <2s, no dropped messages, agents scale correctly

---

### EPIC 2: Prospect Stories - Phase 3 (5 stories)

#### Story 2.13: Validate Product Inquiry Responses
**Theme**: Accuracy of product information
**Example Scenarios**:
- Test suite: 50 product questions with known answers
- Verify: 100% accuracy in ingredients, pricing, availability

#### Story 2.14: Validate Email Capture Flow
**Theme**: Lead generation reliability
**Example Scenarios**:
- Test: prospect provides email for notifications
- Verify: Mailchimp subscriber created with correct tags, confirmation sent

#### Story 2.15: Validate Anonymous User Privacy
**Theme**: No data leakage for unauthenticated users
**Example Scenarios**:
- Prospect asks question
- Verify: no PII logged, conversation not linked to customer database

#### Story 2.16: Validate Conversion Tracking
**Theme**: Analytics integration for prospects
**Example Scenarios**:
- Prospect completes first purchase
- Verify: Google Analytics (mocked) records conversion event

#### Story 2.17: Load Test Prospect Concurrent Sessions
**Theme**: Handle anonymous traffic spikes
**Example Scenarios**:
- Locust test: 100 concurrent anonymous users
- Verify: no session crosstalk, unique conversation contexts

---

### EPIC 3: Support Agent Stories - Phase 3 (3 stories)

#### Story 3.8: Validate Ticket Format Consistency
**Theme**: Zendesk integration quality
**Example Scenarios**:
- Test: 20 different escalation types
- Verify: all tickets have required fields, proper formatting, correct priority

#### Story 3.9: Validate Escalation Response Time
**Theme**: SLA compliance for handoffs
**Example Scenarios**:
- Measure: time from escalation decision to ticket creation
- Verify: <5 seconds, no dropped escalations

#### Story 3.10: Validate Support Notification Delivery
**Theme**: Alert reliability
**Example Scenarios**:
- Test: high-priority ticket created
- Verify: notification logged (email would be sent in production)

---

### EPIC 4: Service Agent Stories - Phase 3 (2 stories)

#### Story 4.4: Validate Service Queue Routing
**Theme**: Correct assignment to service vs support
**Example Scenarios**:
- Test: 20 mixed scenarios (10 service, 10 support)
- Verify: 100% routed to correct queue

#### Story 4.5: Validate Service Case Context
**Theme**: Warranty/product info included in tickets
**Example Scenarios**:
- Test: service request includes purchase date, product SKU
- Verify: all required context present for service resolution

---

### EPIC 5: Sales Agent Stories - Phase 3 (2 stories)

#### Story 5.4: Validate Lead Scoring Accuracy
**Theme**: High-value opportunity detection
**Example Scenarios**:
- Test: 50 conversations (10 high-value, 40 normal)
- Verify: 9/10 high-value leads correctly flagged, <5% false positives

#### Story 5.5: Validate Sales Context Richness
**Theme**: Provide sales team with actionable info
**Example Scenarios**:
- Test: sales ticket includes product interest, quantity, timeline
- Verify: all fields populated, formatted for sales workflow

---

### EPIC 6: AI Customer Assistant Stories - Phase 3 (1 story)

#### Story 6.3: Validate Proactive Engagement Timing
**Theme**: Non-intrusive user experience
**Example Scenarios**:
- Test: AI initiates chat after 5 product views in 10 minutes
- Verify: timing appropriate, message relevant, easy to dismiss

---

### EPIC 7: Operator Stories - Phase 3 (2 stories)

#### Story 7.6: Operator Runs Nightly Regression Suite
**Theme**: Automated quality assurance
**Example Scenarios**:
- GitHub Actions runs full test suite nightly
- Operator reviews results each morning
- Verify: test report emailed, failures clearly highlighted

#### Story 7.7: Operator Generates Performance Report
**Theme**: KPI tracking and reporting
**Example Scenarios**:
- Operator queries observability stack: response times, escalation rates, conversation counts
- System generates report: average response time 1.2s, 72% automation rate
- Verify: metrics align with KPI targets

---

## Phase 4: Production Deployment on Azure ($200/month budget)
**Focus**: Real APIs, multi-language support, Azure infrastructure, production features
**Stories**: 30 stories (2 Customer, 5 Prospect, 3 Support, 6 Service, 6 Sales, 1 AI Assistant, 7 Operator)

### EPIC 1: Customer Stories - Phase 4 (2 stories)

#### Story 1.39: Customer Interacts in Canadian French
**Theme**: Multi-language support
**Example Scenarios**:
- Customer: "Où est ma commande?" (Where is my order?)
- System detects French, routes to response-generator-fr-ca agent
- Response in French with proper formatting

#### Story 1.40: Customer Receives Real-Time Inventory Update
**Theme**: Live Shopify integration
**Example Scenarios**:
- Customer asks about product availability
- System queries real Shopify API (not mock)
- Response reflects actual inventory levels

---

### EPIC 2: Prospect Stories - Phase 4 (5 stories)

#### Story 2.18: Prospect Receives Mailchimp Campaign Follow-Up
**Theme**: Marketing automation integration
**Example Scenarios**:
- Prospect signed up for notifications in Phase 2
- Real Mailchimp campaign sent when product restocked
- Prospect clicks link, AI chat resumes with context

#### Story 2.19: Prospect Interacts in Spanish
**Theme**: Multi-language support for prospects
**Example Scenarios**:
- Prospect: "¿Tienen jabón de rosas?" (Do you have rose soap?)
- System routes to response-generator-es agent
- Response in Spanish with product details

#### Story 2.20: Prospect Tracked via Google Analytics
**Theme**: Real analytics integration
**Example Scenarios**:
- Prospect conversation logged in real Google Analytics
- Operator views funnel: chat → product page → cart → conversion
- Verify: conversion attribution to AI assistant

#### Story 2.21: Prospect Abandons Cart, Receives Email
**Theme**: Cart recovery via Mailchimp
**Example Scenarios**:
- Prospect adds items, leaves site
- AI triggers Mailchimp abandoned cart email
- Email includes: cart contents, discount code, chat resume link

#### Story 2.22: Prospect Converts to Customer
**Theme**: Full funnel tracking
**Example Scenarios**:
- Prospect journey: chat inquiry → email signup → Mailchimp nurture → purchase
- System updates Shopify customer record
- Mailchimp subscriber tagged as "customer"

---

### EPIC 3: Support Agent Stories - Phase 4 (3 stories)

#### Story 3.11: Support Receives Real Zendesk Ticket
**Theme**: Production ticket integration
**Example Scenarios**:
- Customer issue escalated in production
- Real Zendesk ticket created via API
- Support agent sees ticket in their Zendesk dashboard

#### Story 3.12: Support Views Customer History in Zendesk
**Theme**: Context from real Shopify data
**Example Scenarios**:
- Support opens ticket
- Zendesk app sidebar shows: Shopify order history, past tickets, AI conversation log
- Support resolves issue with full context

#### Story 3.13: Support Closes Ticket, Updates Customer
**Theme**: Bi-directional Zendesk integration
**Example Scenarios**:
- Support resolves ticket in Zendesk
- Zendesk webhook notifies AI system
- AI sends customer closure notification via Mailchimp

---

### EPIC 4: Service Agent Stories - Phase 4 (6 stories)

#### Story 4.6: Service Receives Warranty Claim
**Theme**: Post-purchase service workflow
**Example Scenarios**:
- Customer reports defective product within warranty period
- AI verifies purchase date in Shopify
- Escalates to service with warranty status pre-checked

#### Story 4.7: Service Coordinates Replacement Shipment
**Theme**: Service fulfillment via Shopify
**Example Scenarios**:
- Service approves replacement
- Service creates replacement order in Shopify
- Customer receives tracking info automatically

#### Story 4.8: Service Handles Out-of-Warranty Repair
**Theme**: Paid service request
**Example Scenarios**:
- Customer wants repair for product >1 year old
- Service provides repair quote via Zendesk
- If accepted, service creates Shopify invoice for repair fee

#### Story 4.9: Service Tracks Repair Status
**Theme**: Service case lifecycle management
**Example Scenarios**:
- Customer sends product for repair
- Service updates Zendesk ticket with repair milestones
- Customer receives status updates via Mailchimp

#### Story 4.10: Service Escalates Manufacturing Defect
**Theme**: Quality control feedback loop
**Example Scenarios**:
- Multiple customers report same product issue
- Service escalates to operations team
- Product flagged in Shopify for quality review

#### Story 4.11: Service Provides Upgrade Path
**Theme**: Upsell opportunity from service
**Example Scenarios**:
- Customer's product is unrepairable
- Service offers discount on upgraded model
- Shopify discount code generated for customer

---

### EPIC 5: Sales Agent Stories - Phase 4 (6 stories)

#### Story 5.6: Sales Receives Lead from Google Analytics
**Theme**: Behavior-based lead scoring
**Example Scenarios**:
- Google Analytics detects: high-value cart, multiple visits, no purchase
- AI escalates to sales as warm lead
- Sales contacts prospect with targeted offer

#### Story 5.7: Sales Creates Custom Shopify Discount
**Theme**: Negotiated pricing for bulk orders
**Example Scenarios**:
- Sales negotiates 500-unit order
- Sales creates custom discount code in Shopify
- Customer completes purchase with special pricing

#### Story 5.8: Sales Tracks Conversion in CRM
**Theme**: Sales funnel analytics
**Example Scenarios**:
- Sales closes bulk order deal
- Zendesk ticket linked to Shopify order
- Google Analytics records high-value conversion

#### Story 5.9: Sales Nurtures Long-Term Lead
**Theme**: Multi-touch sales process
**Example Scenarios**:
- Prospect expresses interest but not ready to buy
- Sales adds prospect to Mailchimp nurture campaign
- Sales receives notification when prospect re-engages

#### Story 5.10: Sales Coordinates Custom Product Request
**Theme**: Special order handling
**Example Scenarios**:
- Customer wants custom labels for corporate gift
- Sales escalates to operations for quote
- Custom Shopify product created with special pricing

#### Story 5.11: Sales Reviews AI Lead Quality
**Theme**: Continuous improvement feedback
**Example Scenarios**:
- Sales reviews leads from past month
- Sales provides feedback: 80% high-quality, 20% false positives
- Operator adjusts lead scoring thresholds based on feedback

---

### EPIC 6: AI Customer Assistant Stories - Phase 4 (1 story)

#### Story 6.4: AI Proactively Engages Based on Real Analytics
**Theme**: Production behavior tracking
**Example Scenarios**:
- Real Google Analytics detects: customer viewed product 3 times
- AI initiates chat: "I noticed you're interested in the lavender soap. Can I answer any questions?"
- Customer accepts, AI provides personalized recommendations

---

### EPIC 7: Operator Stories - Phase 4 (7 stories)

#### Story 7.8: Operator Deploys to Azure via Terraform
**Theme**: Infrastructure-as-code provisioning
**Example Scenarios**:
- Operator runs `terraform apply` in terraform/phase4_prod/
- Azure resources created: Container Instances, Cosmos DB, Redis, App Gateway
- All services start successfully in Azure

#### Story 7.9: Operator Monitors Azure Costs
**Theme**: Budget compliance
**Example Scenarios**:
- Operator reviews Azure Cost Management dashboard
- Current spend: $145/month (within $200 budget)
- Cost alerts configured at $160 (80%) and $190 (95%)

#### Story 7.10: Operator Configures Azure Key Vault
**Theme**: Secrets management in production
**Example Scenarios**:
- Operator stores: Shopify API key, Zendesk credentials, Mailchimp API key
- Agents retrieve secrets via Managed Identity
- No secrets in code or environment variables

#### Story 7.11: Operator Sets Up Azure DevOps Pipeline
**Theme**: Production CI/CD
**Example Scenarios**:
- Operator creates Azure Pipeline from azure-pipelines.yml
- Pipeline: build Docker images → push to ACR → deploy to Container Instances
- Deployment requires manual approval for production

#### Story 7.12: Operator Reviews Azure Monitor Metrics
**Theme**: Production observability
**Example Scenarios**:
- Operator opens Azure Monitor dashboard
- Metrics: agent response times, error rates, resource utilization
- Alert fires: Intent Classifier response time >2s sustained

#### Story 7.13: Operator Scales Agent Instances
**Theme**: Manual scaling for traffic
**Example Scenarios**:
- Operator anticipates holiday traffic spike
- Operator increases Container Instances from 1 to 3 per agent
- Operator monitors cost impact ($145 → $175)

#### Story 7.14: Operator Performs Cosmos DB Backup
**Theme**: Disaster recovery preparation
**Example Scenarios**:
- Operator verifies continuous backup enabled on Cosmos DB
- Operator tests point-in-time restore to staging environment
- Restore successful, data intact

---

## Phase 5: Production Testing & Go-Live ($200/month budget)
**Focus**: Load testing, security, DR validation, production cutover
**Stories**: 15 stories (0 Customer, 0 Prospect, 2 Support, 4 Service, 4 Sales, 0 AI Assistant, 5 Operator)

### EPIC 3: Support Agent Stories - Phase 5 (2 stories)

#### Story 3.14: Support Validates Production SLA Compliance
**Theme**: Real-world performance testing
**Example Scenarios**:
- Support measures: time from escalation to ticket creation
- Target: <5 seconds, 99.9% success rate
- Verify: production meets SLA

#### Story 3.15: Support Receives High-Priority Alert
**Theme**: Critical issue escalation
**Example Scenarios**:
- Customer reports urgent issue (e.g., "My credit card was charged twice")
- AI escalates immediately, ticket marked "urgent"
- Support receives SMS/email alert (critical priority)

---

### EPIC 4: Service Agent Stories - Phase 5 (4 stories)

#### Story 4.12: Service Handles Production Warranty Claim
**Theme**: Real customer service workflow
**Example Scenarios**:
- First real production warranty claim
- Service uses production Shopify data
- Replacement order created and fulfilled successfully

#### Story 4.13: Service Load Test
**Theme**: Concurrent service case handling
**Example Scenarios**:
- Load test: 10 simultaneous service escalations
- Verify: all tickets created, no data loss, response time <5s

#### Story 4.14: Service Reviews First Month Metrics
**Theme**: Production performance analysis
**Example Scenarios**:
- Operator generates report: 47 service cases, avg resolution time 4.2 hours
- Service reviews escalation accuracy: 92% appropriate
- Service provides feedback for improvements

#### Story 4.15: Service Tests Disaster Recovery
**Theme**: Service continuity validation
**Example Scenarios**:
- Operator simulates Cosmos DB failure
- Service cases restore from backup within 1 hour (RPO target)
- Service resumes processing with no lost tickets

---

### EPIC 5: Sales Agent Stories - Phase 5 (4 stories)

#### Story 5.12: Sales Receives First Production Lead
**Theme**: Real sales opportunity in production
**Example Scenarios**:
- First real customer escalated to sales (bulk order inquiry)
- Sales reviews ticket, all context present
- Sales closes deal, validates tracking in analytics

#### Story 5.13: Sales Load Test
**Theme**: High-value lead handling capacity
**Example Scenarios**:
- Load test: 20 concurrent leads escalated to sales
- Verify: all tickets created, correct priority, no dropped opportunities

#### Story 5.14: Sales Reviews Lead Conversion Rate
**Theme**: ROI validation
**Example Scenarios**:
- Operator generates report: 23 leads, 11 converted (48% conversion)
- Sales reviews: lead quality high, timing appropriate
- System meets business objectives

#### Story 5.15: Sales Tests Disaster Recovery
**Theme**: Revenue-critical data protection
**Example Scenarios**:
- Operator simulates Zendesk failure during active sales negotiation
- Sales ticket data restored from backup
- Sales resumes negotiation with no loss of context

---

### EPIC 7: Operator Stories - Phase 5 (5 stories)

#### Story 7.15: Operator Performs Azure Load Testing
**Theme**: Validate production capacity
**Example Scenarios**:
- Operator runs Azure Load Testing: 100 concurrent users, 1000 req/min
- Agents auto-scale from 1 to 3 instances
- Response time remains <2s, no errors

#### Story 7.16: Operator Runs OWASP ZAP Security Scan
**Theme**: Production security validation
**Example Scenarios**:
- Operator runs ZAP against production endpoints
- Scan reports: no critical vulnerabilities, TLS 1.3 enforced
- Minor findings documented for future improvement

#### Story 7.17: Operator Executes Disaster Recovery Drill
**Theme**: Business continuity validation
**Example Scenarios**:
- Operator simulates: Cosmos DB region failure
- Operator restores from backup to new region
- System recovers within 4-hour RTO target

#### Story 7.18: Operator Performs Cost Optimization Review
**Theme**: Budget management
**Example Scenarios**:
- Operator reviews first month costs: $182 actual vs $200 budget
- Operator identifies: log retention can be reduced from 30 to 7 days (saves $12/month)
- Cost optimization applied, new projected spend: $170/month

#### Story 7.19: Operator Completes Production Cutover
**Theme**: Go-live transition
**Example Scenarios**:
- Operator switches DNS from staging to production
- Real customers begin using system
- Operator monitors for 24 hours: no issues, KPIs met

---

## Summary: Story Distribution by Phase

| Phase | Customer | Prospect | Support | Service | Sales | AI Assist | Operator | **Total** |
|-------|----------|----------|---------|---------|-------|-----------|----------|-----------|
| **Phase 1** | 3 | 2 | 2 | 1 | 1 | 1 | 5 | **15** |
| **Phase 2** | 30 | 10 | 5 | 2 | 2 | 1 | 0 | **50** |
| **Phase 3** | 5 | 5 | 3 | 2 | 2 | 1 | 2 | **20** |
| **Phase 4** | 2 | 5 | 3 | 6 | 6 | 1 | 7 | **30** |
| **Phase 5** | 0 | 0 | 2 | 4 | 4 | 0 | 5 | **15** |
| **TOTAL** | **40** | **25** | **15** | **15** | **15** | **5** | **15** | **130** |

---

## GitHub Issue Labels

**Type Labels**:
- `type: epic` - Top-level actor epic
- `type: feature` - User story implementation
- `type: test` - Testing/validation story

**Priority Labels**:
- `priority: critical` - Must-have for phase completion
- `priority: high` - Important for phase goals
- `priority: medium` - Nice-to-have
- `priority: low` - Future enhancement

**Component Labels**:
- `component: infrastructure` - Docker, networking, deployment
- `component: agent` - AI agent implementation
- `component: api` - API integration (Shopify, Zendesk, Mailchimp)
- `component: observability` - Monitoring, logging, tracing
- `component: testing` - Test infrastructure
- `component: ci-cd` - Automation pipelines
- `component: security` - Security features

**Phase Labels**:
- `phase: phase-1` - Infrastructure & Containers
- `phase: phase-2` - Business Logic
- `phase: phase-3` - Testing & Validation
- `phase: phase-4` - Production Deployment
- `phase: phase-5` - Go-Live

**Actor Labels**:
- `actor: customer` - Customer persona stories
- `actor: prospect` - Prospect persona stories
- `actor: support` - Support agent stories
- `actor: service` - Service agent stories
- `actor: sales` - Sales agent stories
- `actor: ai-assistant` - AI proactive engagement stories
- `actor: operator` - DevOps/admin stories

---

## Next Steps

1. **Review this document** - Validate story distribution and phasing
2. **Generate PowerShell script** - Create GitHub issues from this structure
3. **Create Epic issues first** - 7 top-level epics for actor personas
4. **Create Phase 1 stories** - 15 stories to populate current work
5. **Populate project board** - Add issues to Kanban board
6. **Configure board fields** - Custom fields for Phase, Actor, Priority, Component

**Estimated time to create all 130 issues**: ~15-20 minutes via script

---

*Document Version: 1.0*
*Created: 2026-01-21*
*Author: AI Assistant (Claude)*
*Based on: PROJECT-README.txt, PROJECT-MANAGEMENT-BEST-PRACTICES-FOR-GITHUB.md, blog post content*
