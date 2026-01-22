# Create Phases 3-5 User Stories (65 stories)
# Purpose: Complete the final 65 user stories for testing and production phases
# Estimated runtime: 6-7 minutes

$ErrorActionPreference = "Continue"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating Phases 3-5 User Stories (65 stories)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will take approximately 6-7 minutes..." -ForegroundColor Yellow
Write-Host ""

$totalCreated = 0
$totalErrors = 0
$startTime = Get-Date

# Helper function
function Create-Issue {
    param([string]$Title, [string]$Body, [string]$Labels, [string]$Milestone)
    $tempFile = [System.IO.Path]::GetTempFileName()
    $Body | Out-File -FilePath $tempFile -Encoding UTF8
    try {
        $result = & $ghExe issue create --repo $repo --title $Title --body-file $tempFile --label $Labels --milestone $Milestone 2>&1
        Remove-Item $tempFile -Force
        if ($LASTEXITCODE -eq 0) { return @{ Success = $true; Result = $result } }
        else { return @{ Success = $false; Result = $result } }
    } catch {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        return @{ Success = $false; Result = $_.Exception.Message }
    }
}

function Create-Story {
    param([string]$Number, [string]$Title, [string]$Actor, [string]$Theme, [string]$Scenario1, [string]$Scenario2, [string]$Scenario3, [string]$TechnicalScope, [string]$Criteria1, [string]$Criteria2, [string]$Criteria3, [int]$EpicNumber, [string]$Phase, [string]$Labels, [string]$Milestone)
    $body = @"
## User Story (Story $Number)
As a $Actor
I want $Theme
So that I can achieve my goals

## Example Scenarios
- $Scenario1
- $Scenario2
- $Scenario3

## Technical Scope
$TechnicalScope

## Acceptance Criteria
- [ ] $Criteria1
- [ ] $Criteria2
- [ ] $Criteria3

**Related Epic**: #$EpicNumber
**Phase**: $Phase
"@
    return Create-Issue -Title $Title -Body $body -Labels $Labels -Milestone $Milestone
}

#region Phase 3 Stories (20 stories - Testing & Validation)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 3: Testing & Validation (20 stories)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phase3Count = 0
$phase3Errors = 0

$phase3Stories = @(
    # Customer Testing (5)
    @{ num="1.34"; title="Test: End-to-End Order Status Flow"; actor="Test Engineer"; epic=2; theme="validate order status workflow"; s1="Test script simulates customer order inquiry"; s2="System queries Shopify and responds"; s3="Verify response time <2s, accuracy 100%"; tech="Integration test suite"; c1="Response time meets SLA"; c2="Data accuracy 100%"; c3="No errors in workflow"; labels="type: test,priority: high,component: testing,phase: phase-3,actor: customer" },
    @{ num="1.35"; title="Test: Escalation Accuracy"; actor="Test Engineer"; epic=2; theme="ensure appropriate escalations"; s1="Test suite runs 100 scenarios"; s2="30 should escalate, 70 should not"; s3="Verify precision >90%, recall >95%"; tech="Escalation test framework"; c1="Escalation precision >90%"; c2="Escalation recall >95%"; c3="No false positives in critical cases"; labels="type: test,priority: critical,component: testing,phase: phase-3,actor: customer" },
    @{ num="1.36"; title="Test: Multi-Turn Conversations"; actor="Test Engineer"; epic=2; theme="validate context retention"; s1="Customer asks about order, AI clarifies which one"; s2="Customer provides detail, AI retrieves correct order"; s3="Verify context maintained across turns"; tech="Conversation state testing"; c1="Context preserved >3 turns"; c2="Correct order identified"; c3="No context confusion"; labels="type: test,priority: high,component: agent,phase: phase-3,actor: customer" },
    @{ num="1.37"; title="Test: Error Handling"; actor="Test Engineer"; epic=2; theme="validate graceful degradation"; s1="Mock Shopify returns 500 error"; s2="AI responds with fallback message"; s3="Escalates to support appropriately"; tech="Error injection testing"; c1="Errors handled gracefully"; c2="Customer receives clear message"; c3="Escalation triggered correctly"; labels="type: test,priority: high,component: agent,phase: phase-3,actor: customer" },
    @{ num="1.38"; title="Test: Customer Load Testing"; actor="Test Engineer"; epic=2; theme="validate concurrent capacity"; s1="Locust test: 50 concurrent conversations"; s2="Verify response time <2s under load"; s3="Agents scale correctly"; tech="Load testing framework"; c1="Response time <2s at 50 concurrent"; c2="No dropped messages"; c3="Agents auto-scale"; labels="type: test,priority: critical,component: testing,phase: phase-3,actor: customer" },
    # Prospect Testing (5)
    @{ num="2.13"; title="Test: Product Inquiry Accuracy"; actor="Test Engineer"; epic=3; theme="validate product information accuracy"; s1="Test suite: 50 product questions"; s2="Known correct answers"; s3="Verify 100% accuracy"; tech="Product data validation"; c1="100% accuracy on ingredients"; c2="100% accuracy on pricing"; c3="100% accuracy on availability"; labels="type: test,priority: high,component: agent,phase: phase-3,actor: prospect" },
    @{ num="2.14"; title="Test: Email Capture Flow"; actor="Test Engineer"; epic=3; theme="validate lead generation"; s1="Prospect provides email for notifications"; s2="Mailchimp subscriber created"; s3="Verify correct tags and confirmation"; tech="Integration testing"; c1="Email captured correctly"; c2="Tags applied properly"; c3="Confirmation sent"; labels="type: test,priority: medium,component: api,phase: phase-3,actor: prospect" },
    @{ num="2.15"; title="Test: Anonymous User Privacy"; actor="Test Engineer"; epic=3; theme="ensure no PII leakage"; s1="Prospect asks questions"; s2="Verify no PII logged"; s3="Conversation not linked to customer DB"; tech="Privacy validation testing"; c1="No PII in logs"; c2="Sessions isolated"; c3="No unauthorized data access"; labels="type: test,priority: critical,component: security,phase: phase-3,actor: prospect" },
    @{ num="2.16"; title="Test: Conversion Tracking"; actor="Test Engineer"; epic=3; theme="validate analytics integration"; s1="Prospect completes first purchase"; s2="Google Analytics records conversion"; s3="Verify attribution to AI chat"; tech="Analytics validation"; c1="Conversion event logged"; c2="Attribution correct"; c3="Funnel tracking works"; labels="type: test,priority: medium,component: api,phase: phase-3,actor: prospect" },
    @{ num="2.17"; title="Test: Prospect Load Testing"; actor="Test Engineer"; epic=3; theme="handle anonymous traffic spikes"; s1="Locust: 100 concurrent anonymous users"; s2="Verify no session crosstalk"; s3="Unique contexts maintained"; tech="Load testing"; c1="100 concurrent users supported"; c2="No session mixing"; c3="Performance maintained"; labels="type: test,priority: high,component: testing,phase: phase-3,actor: prospect" },
    # Support/Service/Sales/AI/Operator Testing (10)
    @{ num="3.8"; title="Test: Ticket Format Consistency"; actor="Test Engineer"; epic=4; theme="validate Zendesk integration"; s1="Test 20 different escalation types"; s2="Verify all tickets have required fields"; s3="Proper formatting and priority"; tech="Ticket validation suite"; c1="All required fields present"; c2="Format consistent"; c3="Priority correctly set"; labels="type: test,priority: high,component: api,phase: phase-3,actor: support" },
    @{ num="3.9"; title="Test: Escalation Response Time"; actor="Test Engineer"; epic=4; theme="validate SLA compliance"; s1="Measure escalation to ticket creation time"; s2="Verify <5 seconds"; s3="No dropped escalations"; tech="Performance testing"; c1="Time <5 seconds"; c2="100% success rate"; c3="No data loss"; labels="type: test,priority: critical,component: agent,phase: phase-3,actor: support" },
    @{ num="3.10"; title="Test: Support Notification Delivery"; actor="Test Engineer"; epic=4; theme="validate alert reliability"; s1="High-priority ticket created"; s2="Notification logged"; s3="Verify content and recipients"; tech="Notification testing"; c1="Notifications logged"; c2="Content accurate"; c3="Recipients correct"; labels="type: test,priority: medium,component: api,phase: phase-3,actor: support" },
    @{ num="4.4"; title="Test: Service Queue Routing"; actor="Test Engineer"; epic=5; theme="validate correct routing"; s1="Test 20 mixed scenarios (10 service, 10 support)"; s2="Verify 100% routed correctly"; s3="No misrouting"; tech="Routing validation"; c1="100% routing accuracy"; c2="Service/support properly separated"; c3="Context preserved"; labels="type: test,priority: high,component: agent,phase: phase-3,actor: service" },
    @{ num="4.5"; title="Test: Service Case Context"; actor="Test Engineer"; epic=5; theme="validate required context"; s1="Service request includes purchase date, SKU"; s2="Warranty info present"; s3="All required context verified"; tech="Context validation"; c1="Purchase date included"; c2="Product SKU present"; c3="Warranty status shown"; labels="type: test,priority: medium,component: agent,phase: phase-3,actor: service" },
    @{ num="5.4"; title="Test: Lead Scoring Accuracy"; actor="Test Engineer"; epic=6; theme="validate opportunity detection"; s1="Test 50 conversations (10 high-value, 40 normal)"; s2="Verify 9/10 high-value detected"; s3="<5% false positives"; tech="Lead scoring validation"; c1="Detection rate >90%"; c2="False positive rate <5%"; c3="Context richness >90%"; labels="type: test,priority: high,component: agent,phase: phase-3,actor: sales" },
    @{ num="5.5"; title="Test: Sales Context Richness"; actor="Test Engineer"; epic=6; theme="validate actionable information"; s1="Sales ticket includes product interest, quantity, timeline"; s2="Verify all fields populated"; s3="Formatted for sales workflow"; tech="Context validation"; c1="All required fields present"; c2="Format actionable"; c3="Timeline accurate"; labels="type: test,priority: medium,component: agent,phase: phase-3,actor: sales" },
    @{ num="6.3"; title="Test: Proactive Engagement Timing"; actor="Test Engineer"; epic=7; theme="validate non-intrusive UX"; s1="AI initiates after 5 product views in 10 min"; s2="Timing appropriate"; s3="Easy to dismiss"; tech="Engagement testing"; c1="Timing criteria met"; c2="Message relevant"; c3="Dismissal works"; labels="type: test,priority: medium,component: agent,phase: phase-3,actor: ai-assistant" },
    @{ num="7.6"; title="Operator: Run Nightly Regression Suite"; actor="Operator"; epic=8; theme="automate quality assurance"; s1="GitHub Actions runs tests nightly"; s2="Operator reviews results"; s3="Failures highlighted"; tech="CI/CD automation"; c1="Tests run automatically"; c2="Report emailed"; c3="Failures clear"; labels="type: test,priority: high,component: ci-cd,phase: phase-3,actor: operator" },
    @{ num="7.7"; title="Operator: Generate Performance Report"; actor="Operator"; epic=8; theme="track KPIs"; s1="Operator queries observability stack"; s2="System generates report"; s3="Metrics align with targets"; tech="Reporting automation"; c1="Report generated"; c2="KPIs measured"; c3="Targets validated"; labels="type: feature,priority: medium,component: observability,phase: phase-3,actor: operator" }
)

foreach ($story in $phase3Stories) {
    $result = Create-Story -Number $story.num -Title $story.title -Actor $story.actor -Theme $story.theme -Scenario1 $story.s1 -Scenario2 $story.s2 -Scenario3 $story.s3 -TechnicalScope $story.tech -Criteria1 $story.c1 -Criteria2 $story.c2 -Criteria3 $story.c3 -EpicNumber $story.epic -Phase "3 - Testing" -Labels $story.labels -Milestone "Phase 3 - Testing"
    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase3Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase3Errors++
    }
    Start-Sleep -Milliseconds 500
}

$totalCreated += $phase3Count
$totalErrors += $phase3Errors

Write-Host ""
Write-Host "Phase 3 Complete: $phase3Count created, $phase3Errors errors" -ForegroundColor $(if ($phase3Errors -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

#region Phase 4 Stories (30 stories - Production Deployment)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 4: Production Deployment (30 stories)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phase4Count = 0
$phase4Errors = 0

$phase4Stories = @(
    # Customer/Prospect (7 stories)
    @{ num="1.39"; title="Customer: Multi-Language French Support"; actor="Customer"; epic=2; theme="interact in Canadian French"; s1="Customer asks 'Où est ma commande?'"; s2="System detects French"; s3="Routes to fr-CA response agent"; tech="Language detection, multi-language routing"; c1="French detected correctly"; c2="Response in French"; c3="Proper formatting"; labels="type: feature,priority: high,component: agent,phase: phase-4,actor: customer" },
    @{ num="1.40"; title="Customer: Real-Time Inventory Updates"; actor="Customer"; epic=2; theme="get live product availability"; s1="Customer asks about availability"; s2="System queries real Shopify API"; s3="Real-time inventory displayed"; tech="Live Shopify integration"; c1="Real API integrated"; c2="Inventory accurate"; c3="Response fast"; labels="type: feature,priority: high,component: api,phase: phase-4,actor: customer" },
    @{ num="2.18"; title="Prospect: Mailchimp Campaign Follow-Up"; actor="Prospect"; epic=3; theme="receive marketing automation"; s1="Prospect signed up for restock notifications"; s2="Real Mailchimp campaign sent"; s3="Prospect clicks, chat resumes with context"; tech="Mailchimp automation integration"; c1="Campaign sent"; c2="Link tracking works"; c3="Context preserved"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: prospect" },
    @{ num="2.19"; title="Prospect: Multi-Language Spanish Support"; actor="Prospect"; epic=3; theme="interact in Spanish"; s1="Prospect asks '¿Tienen jabón de rosas?'"; s2="System routes to es response agent"; s3="Response in Spanish"; tech="Language detection, Spanish agent"; c1="Spanish detected"; c2="Response accurate"; c3="Culturally appropriate"; labels="type: feature,priority: high,component: agent,phase: phase-4,actor: prospect" },
    @{ num="2.20"; title="Prospect: Google Analytics Tracking"; actor="Prospect"; epic=3; theme="track funnel in real analytics"; s1="Prospect conversation logged in GA"; s2="Operator views funnel"; s3="Conversion attributed to AI"; tech="Real GA integration"; c1="Events logged"; c2="Funnel visible"; c3="Attribution works"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: prospect" },
    @{ num="2.21"; title="Prospect: Cart Abandonment Email"; actor="Prospect"; epic=3; theme="recover abandoned carts"; s1="Prospect adds items, leaves"; s2="AI triggers Mailchimp email"; s3="Email includes cart and discount"; tech="Abandonment detection, email trigger"; c1="Abandonment detected"; c2="Email sent"; c3="Cart contents accurate"; labels="type: feature,priority: high,component: agent,phase: phase-4,actor: prospect" },
    @{ num="2.22"; title="Prospect: Conversion to Customer"; actor="Prospect"; epic=3; theme="track full funnel"; s1="Prospect journey: chat to purchase"; s2="Shopify customer record updated"; s3="Mailchimp tagged as customer"; tech="Full funnel tracking"; c1="Journey tracked"; c2="Customer record updated"; c3="Tags synchronized"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: prospect" },
    # Support/Service/Sales (15 stories)
    @{ num="3.11"; title="Support: Production Zendesk Integration"; actor="Support Agent"; epic=4; theme="receive real tickets"; s1="Customer escalated in production"; s2="Real Zendesk ticket created"; s3="Support sees in dashboard"; tech="Production Zendesk API"; c1="Tickets created"; c2="Context preserved"; c3="Support workflow seamless"; labels="type: feature,priority: critical,component: api,phase: phase-4,actor: support" },
    @{ num="3.12"; title="Support: Customer History Sidebar"; actor="Support Agent"; epic=4; theme="view full context"; s1="Support opens ticket"; s2="Zendesk sidebar shows Shopify history"; s3="AI conversation log visible"; tech="Zendesk app integration"; c1="History displayed"; c2="Orders shown"; c3="Context complete"; labels="type: feature,priority: high,component: api,phase: phase-4,actor: support" },
    @{ num="3.13"; title="Support: Bi-Directional Updates"; actor="Support Agent"; epic=4; theme="sync ticket closure"; s1="Support resolves ticket"; s2="Zendesk webhook notifies AI"; s3="Customer notified via Mailchimp"; tech="Webhook integration"; c1="Webhook fires"; c2="AI notified"; c3="Customer email sent"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: support" },
    @{ num="4.6"; title="Service: Warranty Claim Validation"; actor="Service Agent"; epic=5; theme="auto-check warranty status"; s1="Customer reports defect"; s2="AI verifies purchase date in Shopify"; s3="Warranty status pre-checked"; tech="Warranty calculation logic"; c1="Purchase date retrieved"; c2="Warranty status calculated"; c3="Escalation includes status"; labels="type: feature,priority: high,component: agent,phase: phase-4,actor: service" },
    @{ num="4.7"; title="Service: Replacement Shipment"; actor="Service Agent"; epic=5; theme="fulfill replacements"; s1="Service approves replacement"; s2="Creates order in Shopify"; s3="Customer receives tracking"; tech="Shopify order creation"; c1="Order created"; c2="Tracking sent"; c3="Customer notified"; labels="type: feature,priority: high,component: api,phase: phase-4,actor: service" },
    @{ num="4.8"; title="Service: Out-of-Warranty Repairs"; actor="Service Agent"; epic=5; theme="quote paid repairs"; s1="Customer wants repair >1 year"; s2="Service provides quote"; s3="Shopify invoice created if accepted"; tech="Invoice generation"; c1="Quote calculated"; c2="Invoice created"; c3="Payment processed"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: service" },
    @{ num="4.9"; title="Service: Repair Status Tracking"; actor="Service Agent"; epic=5; theme="update repair progress"; s1="Customer sends product for repair"; s2="Service updates ticket milestones"; s3="Customer receives status updates"; tech="Status update automation"; c1="Milestones tracked"; c2="Updates sent"; c3="Timeline visible"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: service" },
    @{ num="4.10"; title="Service: Manufacturing Defect Escalation"; actor="Service Agent"; epic=5; theme="flag quality issues"; s1="Multiple customers report same issue"; s2="Service escalates to ops"; s3="Product flagged in Shopify"; tech="Pattern detection, product flagging"; c1="Pattern detected"; c2="Escalation triggered"; c3="Product flagged"; labels="type: feature,priority: low,component: agent,phase: phase-4,actor: service" },
    @{ num="4.11"; title="Service: Upgrade Discount"; actor="Service Agent"; epic=5; theme="offer upgrade path"; s1="Product unrepairable"; s2="Service offers upgraded model discount"; s3="Discount code generated"; tech="Discount code generation"; c1="Discount calculated"; c2="Code created"; c3="Customer receives code"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: service" },
    @{ num="5.6"; title="Sales: Analytics-Based Leads"; actor="Sales Agent"; epic=6; theme="behavioral lead scoring"; s1="GA detects high-value cart, multiple visits"; s2="AI escalates as warm lead"; s3="Sales contacts with targeted offer"; tech="GA integration, lead scoring"; c1="Behavior tracked"; c2="Score calculated"; c3="Lead escalated"; labels="type: feature,priority: high,component: agent,phase: phase-4,actor: sales" },
    @{ num="5.7"; title="Sales: Custom Shopify Discount"; actor="Sales Agent"; epic=6; theme="create negotiated pricing"; s1="Sales negotiates 500-unit order"; s2="Creates custom discount code"; s3="Customer completes purchase"; tech="Shopify discount API"; c1="Code created"; c2="Pricing correct"; c3="Order tracked"; labels="type: feature,priority: high,component: api,phase: phase-4,actor: sales" },
    @{ num="5.8"; title="Sales: Conversion Tracking"; actor="Sales Agent"; epic=6; theme="measure ROI"; s1="Sales closes bulk order"; s2="Zendesk linked to Shopify order"; s3="GA records conversion"; tech="Cross-platform tracking"; c1="Order linked"; c2="Conversion logged"; c3="Revenue attributed"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: sales" },
    @{ num="5.9"; title="Sales: Long-Term Lead Nurture"; actor="Sales Agent"; epic=6; theme="manage extended sales cycles"; s1="Prospect interested but not ready"; s2="Sales adds to Mailchimp campaign"; s3="Notification when re-engaged"; tech="CRM integration, triggers"; c1="Added to nurture"; c2="Re-engagement detected"; c3="Sales notified"; labels="type: feature,priority: medium,component: api,phase: phase-4,actor: sales" },
    @{ num="5.10"; title="Sales: Custom Product Requests"; actor="Sales Agent"; epic=6; theme="handle special orders"; s1="Customer wants custom labels"; s2="Sales escalates to ops for quote"; s3="Custom Shopify product created"; tech="Custom product workflow"; c1="Quote provided"; c2="Product created"; c3="Special pricing applied"; labels="type: feature,priority: low,component: api,phase: phase-4,actor: sales" },
    @{ num="5.11"; title="Sales: Lead Quality Feedback"; actor="Sales Agent"; epic=6; theme="improve lead scoring"; s1="Sales reviews past month leads"; s2="Provides quality feedback"; s3="Operator adjusts thresholds"; tech="Feedback loop, scoring tuning"; c1="Feedback captured"; c2="Thresholds adjusted"; c3="Quality improved"; labels="type: feature,priority: low,component: agent,phase: phase-4,actor: sales" },
    # AI/Operator (8 stories)
    @{ num="6.4"; title="AI: Production Analytics Engagement"; actor="AI Customer Assistant"; epic=7; theme="proactive based on real behavior"; s1="Real GA detects repeat product views"; s2="AI initiates personalized chat"; s3="Customer accepts and converts"; tech="Real-time GA integration"; c1="Detection real-time"; c2="Personalization accurate"; c3="Conversion tracked"; labels="type: feature,priority: medium,component: agent,phase: phase-4,actor: ai-assistant" },
    @{ num="7.8"; title="Operator: Terraform Azure Deployment"; actor="Operator"; epic=8; theme="provision infrastructure"; s1="Operator runs terraform apply"; s2="Azure resources created"; s3="All services start"; tech="Terraform IaC"; c1="Resources provisioned"; c2="Configuration correct"; c3="Services healthy"; labels="type: feature,priority: critical,component: infrastructure,phase: phase-4,actor: operator" },
    @{ num="7.9"; title="Operator: Monitor Azure Costs"; actor="Operator"; epic=8; theme="stay within budget"; s1="Operator reviews Cost Management"; s2="Current spend within budget"; s3="Alerts configured"; tech="Cost monitoring, alerts"; c1="Dashboard accessible"; c2="Spend tracked"; c3="Alerts at 80% and 95%"; labels="type: feature,priority: critical,component: infrastructure,phase: phase-4,actor: operator" },
    @{ num="7.10"; title="Operator: Configure Key Vault"; actor="Operator"; epic=8; theme="secure secrets management"; s1="Operator stores API keys in Key Vault"; s2="Agents retrieve via Managed Identity"; s3="No secrets in code"; tech="Azure Key Vault, Managed Identity"; c1="Secrets stored"; c2="Retrieval works"; c3="Audit logs enabled"; labels="type: feature,priority: critical,component: security,phase: phase-4,actor: operator" },
    @{ num="7.11"; title="Operator: Azure DevOps Pipeline"; actor="Operator"; epic=8; theme="automate production deployment"; s1="Operator creates pipeline"; s2="Build, push, deploy automated"; s3="Manual approval for prod"; tech="Azure DevOps CI/CD"; c1="Pipeline works"; c2="Images pushed to ACR"; c3="Approval gate configured"; labels="type: feature,priority: high,component: ci-cd,phase: phase-4,actor: operator" },
    @{ num="7.12"; title="Operator: Azure Monitor Metrics"; actor="Operator"; epic=8; theme="production observability"; s1="Operator opens Azure Monitor"; s2="Agent metrics visible"; s3="Alerts configured"; tech="Azure Monitor, Application Insights"; c1="Metrics collected"; c2="Dashboard complete"; c3="Alerts fire correctly"; labels="type: feature,priority: high,component: observability,phase: phase-4,actor: operator" },
    @{ num="7.13"; title="Operator: Scale Agent Instances"; actor="Operator"; epic=8; theme="handle traffic spikes"; s1="Operator anticipates holiday traffic"; s2="Scales from 1 to 3 instances"; s3="Monitors cost impact"; tech="Container Instance scaling"; c1="Scaling works"; c2="Performance maintained"; c3="Cost tracked"; labels="type: feature,priority: medium,component: infrastructure,phase: phase-4,actor: operator" },
    @{ num="7.14"; title="Operator: Cosmos DB Backup"; actor="Operator"; epic=8; theme="disaster recovery prep"; s1="Operator verifies continuous backup"; s2="Tests point-in-time restore"; s3="Restore successful"; tech="Cosmos DB backup and restore"; c1="Backup enabled"; c2="Restore tested"; c3="Data intact"; labels="type: feature,priority: high,component: infrastructure,phase: phase-4,actor: operator" }
)

foreach ($story in $phase4Stories) {
    $result = Create-Story -Number $story.num -Title $story.title -Actor $story.actor -Theme $story.theme -Scenario1 $story.s1 -Scenario2 $story.s2 -Scenario3 $story.s3 -TechnicalScope $story.tech -Criteria1 $story.c1 -Criteria2 $story.c2 -Criteria3 $story.c3 -EpicNumber $story.epic -Phase "4 - Production" -Labels $story.labels -Milestone "Phase 4 - Production Deployment"
    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase4Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase4Errors++
    }
    Start-Sleep -Milliseconds 500
}

$totalCreated += $phase4Count
$totalErrors += $phase4Errors

Write-Host ""
Write-Host "Phase 4 Complete: $phase4Count created, $phase4Errors errors" -ForegroundColor $(if ($phase4Errors -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

#region Phase 5 Stories (15 stories - Go-Live)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 5: Go-Live (15 stories)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phase5Count = 0
$phase5Errors = 0

$phase5Stories = @(
    # Support/Service/Sales Production Testing (10 stories)
    @{ num="3.14"; title="Test: Production SLA Compliance"; actor="Test Engineer"; epic=4; theme="validate real-world performance"; s1="Support measures escalation to ticket time"; s2="Target <5s, 99.9% success"; s3="Production meets SLA"; tech="Production performance monitoring"; c1="Time <5 seconds"; c2="Success rate >99.9%"; c3="SLA documented"; labels="type: test,priority: critical,component: testing,phase: phase-5,actor: support" },
    @{ num="3.15"; title="Test: High-Priority Alerts"; actor="Test Engineer"; epic=4; theme="validate critical escalations"; s1="Customer reports urgent issue"; s2="Ticket marked urgent"; s3="SMS/email alert sent"; tech="Alert system testing"; c1="Urgency detected"; c2="Alert sent"; c3="Response time tracked"; labels="type: test,priority: high,component: testing,phase: phase-5,actor: support" },
    @{ num="4.12"; title="Service: Production Warranty Claim"; actor="Service Agent"; epic=5; theme="handle real claims"; s1="First production warranty claim"; s2="Uses real Shopify data"; s3="Replacement fulfilled"; tech="Production workflow"; c1="Claim processed"; c2="Data accurate"; c3="Customer satisfied"; labels="type: feature,priority: high,component: api,phase: phase-5,actor: service" },
    @{ num="4.13"; title="Test: Service Load Test"; actor="Test Engineer"; epic=5; theme="validate concurrent capacity"; s1="10 simultaneous service escalations"; s2="All tickets created"; s3="Response time <5s"; tech="Load testing"; c1="Concurrent handling works"; c2="No data loss"; c3="Performance maintained"; labels="type: test,priority: high,component: testing,phase: phase-5,actor: service" },
    @{ num="4.14"; title="Service: First Month Metrics"; actor="Service Agent"; epic=5; theme="analyze performance"; s1="Operator generates report"; s2="47 service cases, 4.2hr avg resolution"; s3="92% escalation accuracy"; tech="Metrics analysis"; c1="Report generated"; c2="Metrics meet targets"; c3="Feedback captured"; labels="type: feature,priority: medium,component: observability,phase: phase-5,actor: service" },
    @{ num="4.15"; title="Test: Service Disaster Recovery"; actor="Test Engineer"; epic=5; theme="validate continuity"; s1="Simulate Cosmos DB failure"; s2="Restore from backup within 1 hour"; s3="Service resumes with no lost tickets"; tech="DR testing"; c1="RPO met (1 hour)"; c2="RTO met (4 hours)"; c3="No data loss"; labels="type: test,priority: critical,component: testing,phase: phase-5,actor: service" },
    @{ num="5.12"; title="Sales: First Production Lead"; actor="Sales Agent"; epic=6; theme="validate real lead flow"; s1="First real bulk order inquiry escalated"; s2="All context present"; s3="Sales closes deal"; tech="Production validation"; c1="Lead received"; c2="Context complete"; c3="Tracking works"; labels="type: feature,priority: high,component: agent,phase: phase-5,actor: sales" },
    @{ num="5.13"; title="Test: Sales Load Test"; actor="Test Engineer"; epic=6; theme="validate lead handling"; s1="20 concurrent leads"; s2="All tickets created"; s3="No dropped opportunities"; tech="Load testing"; c1="20 leads handled"; c2="Correct priority"; c3="No failures"; labels="type: test,priority: high,component: testing,phase: phase-5,actor: sales" },
    @{ num="5.14"; title="Sales: Lead Conversion Rate"; actor="Sales Agent"; epic=6; theme="measure ROI"; s1="Report: 23 leads, 11 converted (48%)"; s2="Lead quality high"; s3="System meets objectives"; tech="Analytics and reporting"; c1="Conversion rate >40%"; c2="Lead quality validated"; c3="ROI positive"; labels="type: feature,priority: medium,component: observability,phase: phase-5,actor: sales" },
    @{ num="5.15"; title="Test: Sales Disaster Recovery"; actor="Test Engineer"; epic=6; theme="protect revenue data"; s1="Simulate Zendesk failure during negotiation"; s2="Restore from backup"; s3="Sales resumes with context"; tech="DR testing"; c1="Data restored"; c2="Context preserved"; c3="No lost opportunities"; labels="type: test,priority: critical,component: testing,phase: phase-5,actor: sales" },
    # Operator Production Testing (5 stories)
    @{ num="7.15"; title="Operator: Azure Load Testing"; actor="Operator"; epic=8; theme="validate production capacity"; s1="Run Azure Load Test: 100 users, 1000 req/min"; s2="Agents auto-scale 1 to 3 instances"; s3="Response time <2s"; tech="Azure Load Testing"; c1="100 concurrent supported"; c2="Auto-scaling works"; c3="Performance maintained"; labels="type: test,priority: critical,component: testing,phase: phase-5,actor: operator" },
    @{ num="7.16"; title="Operator: OWASP ZAP Security Scan"; actor="Operator"; epic=8; theme="validate security"; s1="Run ZAP against production"; s2="No critical vulnerabilities"; s3="TLS 1.3 enforced"; tech="Security scanning"; c1="No critical findings"; c2="TLS configured"; c3="Findings documented"; labels="type: test,priority: critical,component: security,phase: phase-5,actor: operator" },
    @{ num="7.17"; title="Operator: Disaster Recovery Drill"; actor="Operator"; epic=8; theme="validate business continuity"; s1="Simulate Cosmos DB region failure"; s2="Restore from backup to new region"; s3="Recovery within 4-hour RTO"; tech="Full DR drill"; c1="RPO met (1 hour)"; c2="RTO met (4 hours)"; c3="All services restored"; labels="type: test,priority: critical,component: testing,phase: phase-5,actor: operator" },
    @{ num="7.18"; title="Operator: Cost Optimization Review"; actor="Operator"; epic=8; theme="optimize budget"; s1="Review first month: $182 actual vs $200 budget"; s2="Reduce log retention 30 to 7 days"; s3="New projected spend: $170/month"; tech="Cost management"; c1="Cost reviewed"; c2="Optimizations applied"; c3="Budget compliance maintained"; labels="type: feature,priority: high,component: infrastructure,phase: phase-5,actor: operator" },
    @{ num="7.19"; title="Operator: Production Cutover"; actor="Operator"; epic=8; theme="go-live transition"; s1="Switch DNS to production"; s2="Real customers use system"; s3="Monitor 24 hours, KPIs met"; tech="Production deployment"; c1="Cutover successful"; c2="No downtime"; c3="KPIs achieved"; labels="type: feature,priority: critical,component: infrastructure,phase: phase-5,actor: operator" }
)

foreach ($story in $phase5Stories) {
    $result = Create-Story -Number $story.num -Title $story.title -Actor $story.actor -Theme $story.theme -Scenario1 $story.s1 -Scenario2 $story.s2 -Scenario3 $story.s3 -TechnicalScope $story.tech -Criteria1 $story.c1 -Criteria2 $story.c2 -Criteria3 $story.c3 -EpicNumber $story.epic -Phase "5 - Go-Live" -Labels $story.labels -Milestone "Phase 5 - Go-Live"
    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase5Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase5Errors++
    }
    Start-Sleep -Milliseconds 500
}

$totalCreated += $phase5Count
$totalErrors += $phase5Errors

Write-Host ""
Write-Host "Phase 5 Complete: $phase5Count created, $phase5Errors errors" -ForegroundColor $(if ($phase5Errors -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

#endregion

$elapsed = (Get-Date) - $startTime
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " ALL 130 STORIES COMPLETE!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Final Summary:" -ForegroundColor Yellow
Write-Host "  Phase 3 Created: $phase3Count issues" -ForegroundColor Green
Write-Host "  Phase 4 Created: $phase4Count issues" -ForegroundColor Green
Write-Host "  Phase 5 Created: $phase5Count issues" -ForegroundColor Green
Write-Host "  Total Created: $totalCreated issues" -ForegroundColor Green
Write-Host "  Total Errors: $totalErrors issues" -ForegroundColor $(if ($totalErrors -eq 0) { "Green" } else { "Red" })
Write-Host "  Elapsed Time: $($elapsed.Minutes)m $($elapsed.Seconds)s" -ForegroundColor Gray
Write-Host ""
Write-Host "Complete Issue List:" -ForegroundColor Cyan
Write-Host "  - 7 Epics (#2-#8)" -ForegroundColor White
Write-Host "  - 15 Phase 1 (#9-#23)" -ForegroundColor White
Write-Host "  - 50 Phase 2 (#24-#73)" -ForegroundColor White
Write-Host "  - 20 Phase 3 (#74-#93)" -ForegroundColor White
Write-Host "  - 30 Phase 4 (#94-#123)" -ForegroundColor White
Write-Host "  - 15 Phase 5 (#124-#138)" -ForegroundColor White
Write-Host "  TOTAL: 137 issues (7 epics + 130 stories)" -ForegroundColor Yellow
Write-Host ""
Write-Host "View all issues: https://github.com/$repo/issues" -ForegroundColor Cyan
Write-Host "Project board: https://github.com/orgs/Remaker-Digital/projects/1" -ForegroundColor Cyan
Write-Host ""
