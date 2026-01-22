# Create Remaining 115 User Stories (Phases 2-5)
# Purpose: Complete the full 130-story backlog
# Estimated runtime: 12-15 minutes (115 stories × 500ms delay)

$ErrorActionPreference = "Continue"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating 115 Remaining User Stories (Phases 2-5)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will take approximately 12-15 minutes..." -ForegroundColor Yellow
Write-Host "Progress will be shown for each phase..." -ForegroundColor Gray
Write-Host ""

$totalCreated = 0
$totalErrors = 0
$startTime = Get-Date

# Helper function to create issue
function Create-Issue {
    param(
        [string]$Title,
        [string]$Body,
        [string]$Labels,
        [string]$Milestone
    )

    $tempFile = [System.IO.Path]::GetTempFileName()
    $Body | Out-File -FilePath $tempFile -Encoding UTF8

    try {
        $result = & $ghExe issue create `
            --repo $repo `
            --title $Title `
            --body-file $tempFile `
            --label $Labels `
            --milestone $Milestone 2>&1

        Remove-Item $tempFile -Force

        if ($LASTEXITCODE -eq 0) {
            return @{ Success = $true; Result = $result }
        } else {
            return @{ Success = $false; Result = $result }
        }
    } catch {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        return @{ Success = $false; Result = $_.Exception.Message }
    }
}

# Helper to create story with consistent format
function Create-Story {
    param(
        [string]$Number,
        [string]$Title,
        [string]$Actor,
        [string]$Theme,
        [string]$Scenario1,
        [string]$Scenario2,
        [string]$Scenario3,
        [string]$TechnicalScope,
        [string]$Criteria1,
        [string]$Criteria2,
        [string]$Criteria3,
        [int]$EpicNumber,
        [string]$Phase,
        [string]$Labels,
        [string]$Milestone
    )

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

#region Phase 2 Stories (50 stories)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 2: Business Logic (50 stories)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phase2Count = 0
$phase2Errors = 0

# Customer Stories 1.4-1.33 (30 stories)
Write-Host "[Phase 2] Creating 30 Customer stories..." -ForegroundColor Yellow

$customerP2Stories = @(
    @{ num="1.4"; title="Customer: Order Status with Tracking Details"; theme="check order status with detailed tracking"; s1="Customer asks 'Where is order #10234?'"; s2="System retrieves from mock Shopify: status, tracking, carrier, ETA"; s3="Response includes full tracking details"; tech="Enhanced Shopify integration, tracking API"; c1="Tracking number displayed"; c2="Carrier and ETA shown"; c3="Real-time status updates" },
    @{ num="1.5"; title="Customer: Order Modification Request"; theme="change order details before shipment"; s1="Customer wants to change shipping address"; s2="System checks if order can be modified"; s3="Provides instructions or escalates"; tech="Shopify order API, modification logic"; c1="Pre-shipment modifications allowed"; c2="Post-shipment escalates"; c3="Clear instructions provided" },
    @{ num="1.6"; title="Customer: Return/Refund Inquiry"; theme="understand return process"; s1="Customer wants to return irritating soap"; s2="System retrieves return policy"; s3="Provides return instructions"; tech="Knowledge base, policy retrieval"; c1="Return policy clearly explained"; c2="Instructions actionable"; c3="Escalation for complex cases" },
    @{ num="1.7"; title="Customer: Product Recommendation Based on History"; theme="receive personalized suggestions"; s1="Customer asks for complementary products"; s2="System analyzes purchase history"; s3="Suggests related items"; tech="Purchase history analysis, recommendation engine"; c1="Recommendations relevant"; c2="Based on actual history"; c3="Includes product details" },
    @{ num="1.8"; title="Customer: Reorder Previous Purchase"; theme="quickly repurchase previous items"; s1="Customer wants to reorder last month's purchase"; s2="System retrieves order history"; s3="Generates cart link"; tech="Order history retrieval, cart generation"; c1="Previous items identified"; c2="Cart link functional"; c3="Quantities preserved" },
    @{ num="1.9"; title="Customer: Delivery Issue - Not Received"; theme="report missing delivery"; s1="Package marked delivered but not received"; s2="System escalates immediately (high priority)"; s3="Zendesk ticket with all context"; tech="Escalation logic, priority handling"; c1="Immediate escalation"; c2="High priority ticket"; c3="All context preserved" },
    @{ num="1.10"; title="Customer: Product Quality Complaint"; theme="report defective or wrong product"; s1="Received different scent than ordered"; s2="System gathers order and product details"; s3="Escalates with replacement options"; tech="Issue gathering, escalation"; c1="Problem clearly documented"; c2="Escalation includes options"; c3="Customer receives acknowledgment" },
    @{ num="1.11"; title="Customer: Subscription Management"; theme="modify recurring orders"; s1="Customer wants to pause subscription"; s2="System checks subscription status"; s3="Provides pause/cancel options"; tech="Shopify subscription API"; c1="Current status displayed"; c2="Modification options clear"; c3="Changes confirmed" },
    @{ num="1.12"; title="Customer: Gift Order Inquiry"; theme="send order as gift"; s1="Customer asks about gift options"; s2="System retrieves gift settings"; s3="Explains wrapping and messages"; tech="Gift options configuration"; c1="Gift options explained"; c2="Pricing included"; c3="Separate shipping available" },
    @{ num="1.13"; title="Customer: Bulk Purchase Discount"; theme="get pricing for large orders"; s1="Customer asks about 50+ unit discounts"; s2="System provides tiered pricing"; s3="Or escalates to sales"; tech="Pricing tiers, sales routing"; c1="Bulk pricing shown"; c2="Sales escalation for custom"; c3="Clear quantity thresholds" },
    @{ num="1.14"; title="Customer: Loyalty Program Inquiry"; theme="check rewards status"; s1="Customer asks about points balance"; s2="System retrieves loyalty data"; s3="Explains balance and redemption"; tech="Loyalty system integration"; c1="Current balance shown"; c2="Redemption options clear"; c3="Earning rate explained" },
    @{ num="1.15"; title="Customer: Shipping Cost Question"; theme="understand delivery pricing"; s1="Customer asks about shipping to Canada"; s2="System retrieves shipping rates"; s3="Provides rates by carrier and speed"; tech="Shipping rate API"; c1="Rates accurate"; c2="Multiple options shown"; c3="Delivery times included" },
    @{ num="1.16"; title="Customer: Order Cancellation Request"; theme="cancel order before shipment"; s1="Customer wants to cancel order"; s2="System checks order status"; s3="Confirms cancellation or explains return"; tech="Order status check, cancellation API"; c1="Pre-ship cancellation works"; c2="Post-ship return process explained"; c3="Refund timeline stated" },
    @{ num="1.17"; title="Customer: Promo Code Application"; theme="use discount code"; s1="Customer's promo code not working"; s2="System validates code"; s3="Explains eligibility or applies code"; tech="Promo code validation"; c1="Code validation accurate"; c2="Eligibility clearly explained"; c3="Application successful" },
    @{ num="1.18"; title="Customer: Product Comparison"; theme="compare product options"; s1="Customer asks difference between soaps"; s2="System retrieves details for both"; s3="Compares ingredients and benefits"; tech="Product comparison logic"; c1="Side-by-side comparison"; c2="Key differences highlighted"; c3="Customer reviews included" },
    @{ num="1.19"; title="Customer: Allergy/Ingredient Concern"; theme="identify safe products"; s1="Customer allergic to coconut oil"; s2="System filters by ingredient"; s3="Lists safe options"; tech="Ingredient filtering"; c1="Accurate filtering"; c2="All safe options shown"; c3="Warnings for unsafe products" },
    @{ num="1.20"; title="Customer: International Shipping Inquiry"; theme="ship to another country"; s1="Customer asks about UK shipping"; s2="System checks shipping zones"; s3="Provides international rates and customs info"; tech="International shipping config"; c1="Zone coverage accurate"; c2="Customs info included"; c3="Delivery times realistic" },
    @{ num="1.21"; title="Customer: Payment Method Issue"; theme="resolve checkout problems"; s1="Credit card declined"; s2="System provides troubleshooting"; s3="Suggests alternatives or escalates"; tech="Payment troubleshooting logic"; c1="Common issues addressed"; c2="Alternative methods suggested"; c3="Escalation for persistent issues" },
    @{ num="1.22"; title="Customer: Order History Review"; theme="view past purchases"; s1="Customer asks what they ordered in December"; s2="System retrieves order history"; s3="Lists orders with dates and products"; tech="Order history retrieval"; c1="Complete history shown"; c2="Date filtering works"; c3="Product details included" },
    @{ num="1.23"; title="Customer: Wholesale Inquiry"; theme="get business pricing"; s1="Spa owner asks about wholesale"; s2="System provides wholesale info"; s3="Escalates to sales"; tech="Wholesale detection, sales routing"; c1="Wholesale program explained"; c2="Sales escalation automatic"; c3="Application process clear" },
    @{ num="1.24"; title="Customer: Backorder Status"; theme="know when product restocks"; s1="Customer asks when mango soap returns"; s2="System checks inventory"; s3="Provides ETA or notification signup"; tech="Inventory checking, notification signup"; c1="Current status accurate"; c2="ETA provided if available"; c3="Notification signup works" },
    @{ num="1.25"; title="Customer: Email Preference Management"; theme="control marketing emails"; s1="Customer receiving too many emails"; s2="System provides unsubscribe link"; s3="Offers frequency reduction"; tech="Mailchimp integration"; c1="Unsubscribe link works"; c2="Frequency options available"; c3="Preferences saved" },
    @{ num="1.26"; title="Customer: Account Login Issue"; theme="reset password"; s1="Customer forgot password"; s2="System provides reset link"; s3="Escalates if account locked"; tech="Password reset flow"; c1="Reset link sent"; c2="Instructions clear"; c3="Security checks in place" },
    @{ num="1.27"; title="Customer: Gift Card Balance"; theme="check gift card value"; s1="Customer asks gift card balance"; s2="System queries Shopify"; s3="Provides balance and expiration"; tech="Gift card API"; c1="Balance accurate"; c2="Expiration shown"; c3="Usage instructions provided" },
    @{ num="1.28"; title="Customer: Store Location/Hours Inquiry"; theme="visit physical store"; s1="Customer asks about physical location"; s2="System retrieves store info"; s3="Provides address, hours, or online-only notice"; tech="Store information knowledge base"; c1="Info accurate"; c2="Hours current"; c3="Directions provided" },
    @{ num="1.29"; title="Customer: Corporate/Bulk Order"; theme="order large quantity for event"; s1="Need 200 soaps for wedding"; s2="System detects large quantity"; s3="Escalates to sales"; tech="Quantity detection, sales escalation"; c1="Large orders detected"; c2="Sales escalation automatic"; c3="Custom pricing offered" },
    @{ num="1.30"; title="Customer: Sustainability/Ethical Sourcing"; theme="learn about company values"; s1="Customer asks if cruelty-free"; s2="System retrieves policy"; s3="Provides certifications and sourcing"; tech="Policy knowledge base"; c1="Policy clearly stated"; c2="Certifications listed"; c3="Sourcing details provided" },
    @{ num="1.31"; title="Customer: Special Occasion Deadline"; theme="receive by specific date"; s1="Need item by Friday for birthday"; s2="System calculates delivery time"; s3="Suggests expedited or escalates"; tech="Delivery time calculation"; c1="Delivery estimate accurate"; c2="Expedited options shown"; c3="Escalation for tight timelines" },
    @{ num="1.32"; title="Customer: Product Customization Request"; theme="personalize products"; s1="Customer wants custom labels"; s2="System checks if available"; s3="Explains options or escalates"; tech="Customization options config"; c1="Options clearly explained"; c2="Pricing included"; c3="Custom orders escalated" },
    @{ num="1.33"; title="Customer: Warranty/Guarantee Question"; theme="understand satisfaction policy"; s1="Customer asks about guarantee"; s2="System retrieves policy"; s3="Explains timeframes and conditions"; tech="Policy knowledge base"; c1="Policy complete"; c2="Timeframes clear"; c3="Process explained" }
)

foreach ($story in $customerP2Stories) {
    $result = Create-Story `
        -Number $story.num `
        -Title $story.title `
        -Actor "Customer" `
        -Theme $story.theme `
        -Scenario1 $story.s1 `
        -Scenario2 $story.s2 `
        -Scenario3 $story.s3 `
        -TechnicalScope $story.tech `
        -Criteria1 $story.c1 `
        -Criteria2 $story.c2 `
        -Criteria3 $story.c3 `
        -EpicNumber 2 `
        -Phase "2 - Business Logic" `
        -Labels "type: feature,priority: high,component: agent,phase: phase-2,actor: customer" `
        -Milestone "Phase 2 - Business Logic"

    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase2Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase2Errors++
    }

    Start-Sleep -Milliseconds 500
}

# Prospect Stories 2.3-2.12 (10 stories)
Write-Host ""
Write-Host "[Phase 2] Creating 10 Prospect stories..." -ForegroundColor Yellow

$prospectP2Stories = @(
    @{ num="2.3"; title="Prospect: Product Discovery"; theme="browse available products"; s1="Prospect asks what types of soap available"; s2="System lists categories"; s3="Provides top sellers"; tech="Product catalog API"; c1="Categories complete"; c2="Top sellers shown"; c3="Seasonal items included" },
    @{ num="2.4"; title="Prospect: Ingredient Question"; theme="research product details"; s1="Prospect asks about eucalyptus ingredients"; s2="System retrieves details"; s3="Lists ingredients and benefits"; tech="Product detail retrieval"; c1="Ingredients accurate"; c2="Benefits explained"; c3="Usage instructions provided" },
    @{ num="2.5"; title="Prospect: Price Comparison"; theme="understand value proposition"; s1="Why $12 vs $3 drugstore soap?"; s2="System explains organic, handmade, sustainability"; s3="Links to values page"; tech="Value proposition content"; c1="Differentiators clear"; c2="Quality explained"; c3="Link to more info provided" },
    @{ num="2.6"; title="Prospect: Email List Signup"; theme="receive sale notifications"; s1="Prospect wants sale alerts"; s2="System prompts for email"; s3="Creates Mailchimp subscriber"; tech="Mailchimp integration"; c1="Email captured"; c2="Tag applied correctly"; c3="Confirmation sent" },
    @{ num="2.7"; title="Prospect: Out-of-Stock Notification"; theme="waitlist for product"; s1="Rose soap sold out, notify when back"; s2="System captures email and product"; s3="Creates tagged subscriber"; tech="Waitlist management"; c1="Product interest tracked"; c2="Notification configured"; c3="Confirmation provided" },
    @{ num="2.8"; title="Prospect: First-Time Buyer Discount"; theme="get new customer incentive"; s1="Prospect asks about discounts"; s2="System provides first-order code"; s3="Explains terms"; tech="Promo code system"; c1="Code provided"; c2="Terms clear"; c3="Expiration stated" },
    @{ num="2.9"; title="Prospect: Shipping Policy Question"; theme="understand delivery time"; s1="How long does shipping take?"; s2="System retrieves policy"; s3="Explains times by region"; tech="Shipping policy content"; c1="Times accurate"; c2="Regional differences noted"; c3="Expedited options mentioned" },
    @{ num="2.10"; title="Prospect: Return Policy Question"; theme="reduce purchase risk"; s1="What if I don't like it?"; s2="System explains return policy"; s3="Emphasizes satisfaction guarantee"; tech="Return policy content"; c1="Policy complete"; c2="Guarantee emphasized"; c3="Process clear" },
    @{ num="2.11"; title="Prospect: Gift Suggestion"; theme="find gift for someone"; s1="Looking for lavender gift"; s2="System suggests lavender products"; s3="Offers gift options"; tech="Product recommendation, gift features"; c1="Relevant suggestions"; c2="Gift options explained"; c3="Multiple price points" },
    @{ num="2.12"; title="Prospect: Sample Request"; theme="try before buying"; s1="Do you sell samples?"; s2="System checks for trial sizes"; s3="Explains sample or starter options"; tech="Product catalog filtering"; c1="Sample availability accurate"; c2="Starter sets suggested"; c3="Pricing included" }
)

foreach ($story in $prospectP2Stories) {
    $result = Create-Story `
        -Number $story.num `
        -Title $story.title `
        -Actor "Prospect" `
        -Theme $story.theme `
        -Scenario1 $story.s1 `
        -Scenario2 $story.s2 `
        -Scenario3 $story.s3 `
        -TechnicalScope $story.tech `
        -Criteria1 $story.c1 `
        -Criteria2 $story.c2 `
        -Criteria3 $story.c3 `
        -EpicNumber 3 `
        -Phase "2 - Business Logic" `
        -Labels "type: feature,priority: medium,component: agent,phase: phase-2,actor: prospect" `
        -Milestone "Phase 2 - Business Logic"

    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase2Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase2Errors++
    }

    Start-Sleep -Milliseconds 500
}

# Support, Service, Sales, AI Assistant stories (10 more for Phase 2)
Write-Host ""
Write-Host "[Phase 2] Creating 10 more stories (Support/Service/Sales/AI)..." -ForegroundColor Yellow

$miscP2Stories = @(
    @{ num="3.3"; title="Support: Review Escalated Ticket"; actor="Support Agent"; epic=4; theme="receive AI-escalated cases"; s1="Support opens AI-created ticket"; s2="Ticket includes full transcript and context"; s3="Support continues seamlessly"; tech="Context preservation in tickets"; c1="Full transcript included"; c2="Order history attached"; c3="Reason for escalation noted"; labels="type: feature,priority: high,component: api,phase: phase-2,actor: support" },
    @{ num="3.4"; title="Support: Request Additional Context"; actor="Support Agent"; epic=4; theme="get more info from AI"; s1="Support needs clarification"; s2="Support queries AI system"; s3="AI provides additional context"; tech="Support-AI communication"; c1="Query interface works"; c2="Context provided quickly"; c3="Information actionable"; labels="type: feature,priority: medium,component: agent,phase: phase-2,actor: support" },
    @{ num="3.5"; title="Support: Resolve and Close Ticket"; actor="Support Agent"; epic=4; theme="complete case resolution"; s1="Support resolves issue"; s2="Support closes Zendesk ticket"; s3="Customer notified via Mailchimp"; tech="Ticket closure workflow"; c1="Resolution logged"; c2="Ticket closed properly"; c3="Customer notification sent"; labels="type: feature,priority: high,component: api,phase: phase-2,actor: support" },
    @{ num="3.6"; title="Support: Escalate to Management"; actor="Support Agent"; epic=4; theme="elevate complex cases"; s1="Customer demands refund outside policy"; s2="Support escalates to manager"; s3="Manager receives with notes"; tech="Internal escalation workflow"; c1="Manager queue works"; c2="Notes preserved"; c3="Recommendation included"; labels="type: feature,priority: medium,component: agent,phase: phase-2,actor: support" },
    @{ num="3.7"; title="Support: Update Knowledge Base"; actor="Support Agent"; epic=4; theme="improve AI responses"; s1="Support notices repeated escalations"; s2="Support adds answer to KB"; s3="AI updated for future queries"; tech="Knowledge base management"; c1="KB entry created"; c2="AI can access new info"; c3="Escalations reduced"; labels="type: feature,priority: low,component: agent,phase: phase-2,actor: support" },
    @{ num="4.2"; title="Service: Receive Repair Request"; actor="Service Agent"; epic=5; theme="handle product repairs"; s1="Customer's pump broke"; s2="Ticket includes purchase date and SKU"; s3="Service initiates warranty replacement"; tech="Service ticket context"; c1="Warranty status checked"; c2="Product details included"; c3="Replacement process started"; labels="type: feature,priority: medium,component: agent,phase: phase-2,actor: service" },
    @{ num="4.3"; title="Service: Coordinate Upgrade"; actor="Service Agent"; epic=5; theme="process subscription upgrades"; s1="Customer wants quarterly instead of monthly"; s2="Service reviews account"; s3="Processes upgrade"; tech="Subscription management"; c1="Account changes processed"; c2="Customer confirmed"; c3="Billing updated"; labels="type: feature,priority: medium,component: agent,phase: phase-2,actor: service" },
    @{ num="5.2"; title="Sales: Receive High-Value Lead"; actor="Sales Agent"; epic=6; theme="get qualified prospects"; s1="Prospect inquired about 500-unit order"; s2="Ticket includes conversation and interest"; s3="Sales reaches out with quote"; tech="Lead handoff workflow"; c1="Lead context complete"; c2="Contact info accurate"; c3="Product interest noted"; labels="type: feature,priority: high,component: agent,phase: phase-2,actor: sales" },
    @{ num="5.3"; title="Sales: Convert Lead"; actor="Sales Agent"; epic=6; theme="close opportunities"; s1="Sales negotiates pricing"; s2="Sales creates custom invoice"; s3="Opportunity tracked in GA"; tech="Sales conversion tracking"; c1="Invoice created"; c2="Discount applied"; c3="Conversion logged"; labels="type: feature,priority: high,component: agent,phase: phase-2,actor: sales" },
    @{ num="6.2"; title="AI Assistant: Cart Recovery"; actor="AI Customer Assistant"; epic=7; theme="re-engage abandoned carts"; s1="GA detects cart abandonment"; s2="AI initiates chat or email"; s3="Customer returns and purchases"; tech="Abandonment detection, proactive engagement"; c1="Abandonment detected"; c2="Engagement initiated"; c3="Conversion tracked"; labels="type: feature,priority: medium,component: agent,phase: phase-2,actor: ai-assistant" }
)

foreach ($story in $miscP2Stories) {
    $result = Create-Story `
        -Number $story.num `
        -Title $story.title `
        -Actor $story.actor `
        -Theme $story.theme `
        -Scenario1 $story.s1 `
        -Scenario2 $story.s2 `
        -Scenario3 $story.s3 `
        -TechnicalScope $story.tech `
        -Criteria1 $story.c1 `
        -Criteria2 $story.c2 `
        -Criteria3 $story.c3 `
        -EpicNumber $story.epic `
        -Phase "2 - Business Logic" `
        -Labels $story.labels `
        -Milestone "Phase 2 - Business Logic"

    if ($result.Success) {
        Write-Host "  [OK] $($story.title)" -ForegroundColor Green
        $phase2Count++
    } else {
        Write-Host "  [ERROR] $($story.title): $($result.Result)" -ForegroundColor Red
        $phase2Errors++
    }

    Start-Sleep -Milliseconds 500
}

$totalCreated += $phase2Count
$totalErrors += $phase2Errors

Write-Host ""
Write-Host "Phase 2 Complete: $phase2Count created, $phase2Errors errors" -ForegroundColor $(if ($phase2Errors -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

# Continue with Phase 3, 4, 5...
# (Script continues in next section due to length)

$elapsed = (Get-Date) - $startTime
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Partial Complete - Phase 2 Done!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Phase 2 Created: $phase2Count issues" -ForegroundColor Green
Write-Host "  Errors: $phase2Errors issues" -ForegroundColor $(if ($phase2Errors -eq 0) { "Green" } else { "Red" })
Write-Host "  Elapsed Time: $($elapsed.Minutes)m $($elapsed.Seconds)s" -ForegroundColor Gray
Write-Host ""
Write-Host "Remaining: Phases 3, 4, 5 (65 stories)" -ForegroundColor Yellow
Write-Host "Next: Run create-phases-3-4-5.ps1 to complete" -ForegroundColor Cyan
Write-Host ""
