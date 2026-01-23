# GitHub Templates Summary

**Date Created:** 2026-01-22
**Purpose:** Issue reporting templates and enhanced contribution guidelines

## Files Created

### Issue Templates (`.github/ISSUE_TEMPLATE/`)

#### 1. Bug Report (`bug_report.yml`)
Structured template for reporting bugs with:
- **Phase selection:** Which project phase is affected (Phase 1-5)
- **Component selection:** Agent, Mock API, Infrastructure, etc.
- **Required fields:**
  - Bug description
  - Steps to reproduce
  - Expected vs. actual behavior
  - Environment details (OS, Python, Docker versions)
  - Environment type (Local/Azure Staging/Azure Production)
- **Optional fields:**
  - Relevant logs (with shell rendering)
  - Additional context
- **Pre-submission checklist** to ensure quality reports

**Labels:** `bug`, `needs-triage`

#### 2. Feature Request (`feature_request.yml`)
Comprehensive template for suggesting new features:
- **Phase targeting:** When should this feature be implemented
- **Component category:** Which area it affects
- **Required fields:**
  - Problem statement (what problem does it solve)
  - Proposed solution
  - Acceptance criteria
  - Priority level
- **Project-specific fields:**
  - Educational value assessment (High/Medium/Low)
  - Budget impact for Phase 4-5 ($200/month constraint)
  - Implementation approach
- **Guardrails:** Reminds contributors about budget constraints and AGNTCY SDK patterns
- **Pre-submission checklist** for alignment with project goals

**Labels:** `enhancement`, `needs-triage`

#### 3. Documentation Issue (`documentation.yml`)
Specialized template for documentation improvements:
- **Documentation type:** README, CONTRIBUTING, code comments, guides, etc.
- **Issue type:** Missing, Unclear, Incorrect, Outdated, Incomplete, Formatting
- **Required fields:**
  - Specific location (file, section, line numbers)
  - Problem description
  - Target audience (who benefits)
  - Impact level (Critical to Low)
- **Optional fields:**
  - Suggested improvement
  - Related code/files

**Labels:** `documentation`, `needs-triage`

#### 4. Cost Optimization (`cost_optimization.yml`)
**Unique template** reflecting the project's key learning objective:
- **Service targeting:** Which Azure service to optimize
- **Required fields:**
  - Current cost estimate (with calculations)
  - Proposed optimization
  - Projected cost savings (with percentages)
  - Trade-offs and limitations
  - Performance impact assessment
- **Implementation details:**
  - Step-by-step approach
  - Testing status
  - Supporting evidence (Azure pricing links, calculators)
- **Educational value:** How well does it teach cost optimization concepts
- **Budget validation:** Ensures total stays under $200/month

**Labels:** `cost-optimization`, `enhancement`, `needs-triage`

#### 5. Template Configuration (`config.yml`)
Controls issue template behavior:
- **Disables blank issues:** Forces template usage
- **Contact links:**
  - GitHub Discussions (general questions)
  - Security Advisories (private vulnerability reporting)
  - AGNTCY SDK Documentation (SDK-specific questions)
  - Project Documentation (complete specifications)

## CONTRIBUTING.md Enhancements

Updated the existing `CONTRIBUTING.md` with new sections:

### New Sections Added

1. **Reporting Issues** (comprehensive guide)
   - When to use each template
   - What information to include
   - Important considerations for each type

2. **Community Guidelines**
   - Code of conduct for educational project
   - Response time expectations
   - Contributor recognition

3. **Advanced Topics**
   - Working with AGNTCY SDK (factory pattern, A2A/MCP protocols)
   - Testing with Docker Compose
   - Phase-specific contribution guidance
   - Cost awareness for Azure services

4. **Troubleshooting Contributions**
   - Common CI/CD failures and fixes
   - Docker build issues
   - Test coverage problems
   - Code quality checks

## Design Decisions

### Why YAML Templates?
- **Structured data:** GitHub parses YAML into form fields
- **Better UX:** Dropdown menus, checkboxes, validation
- **Quality control:** Required fields ensure complete information
- **Consistency:** All issues follow same format

### Why 4 Templates?
Each template serves a distinct purpose:
1. **Bug Report:** Technical issues and errors
2. **Feature Request:** New capabilities and enhancements
3. **Documentation:** Knowledge and clarity improvements
4. **Cost Optimization:** Budget-focused suggestions (unique to this project)

This covers the most common contribution types for an educational infrastructure project.

### Budget Awareness
Cost optimization is woven throughout:
- Dedicated Cost Optimization template
- Budget impact field in Feature Request template
- Cost awareness section in CONTRIBUTING.md
- Examples of good/bad Azure service choices

This reflects the **$200/month constraint** as a key learning objective.

### Educational Focus
Every template emphasizes educational value:
- "Educational value" dropdown in templates
- Alignment with learning goals in checklists
- Code examples in CONTRIBUTING.md
- Focus on teaching, not just building

### Phase-Aware
Templates recognize the 5-phase structure:
- Phase selection dropdowns
- Phase-specific contribution guidance
- Different constraints per phase ($0 vs $200/month)

## Template Features

### Smart Defaults
- Auto-populated labels (`bug`, `enhancement`, `documentation`)
- Issue title prefixes (`[Bug]:`, `[Feature]:`, `[Docs]:`, `[Cost]:`)
- Pre-filled environment sections

### Validation
- Required fields prevent incomplete submissions
- Dropdowns ensure consistent categorization
- Checklists prompt contributors to verify quality

### Context-Aware
- Budget reminders where relevant
- AGNTCY SDK pattern references
- Links to project documentation
- Phase-specific considerations

### Rendering
- Markdown rendering for formatted text
- Shell rendering for log outputs
- Structured fields for dropdowns

## Usage Examples

### Reporting a Bug
1. Go to [New Issue](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues/new/choose)
2. Select "Bug Report"
3. Fill in:
   - Phase: "Phase 1 - Infrastructure & Containers"
   - Component: "Agent - Intent Classification"
   - Description: "Agent crashes when processing empty message"
   - Steps to reproduce: [detailed steps]
   - Logs: [paste from `docker-compose logs`]
4. Submit → Auto-labeled `bug`, `needs-triage`

### Suggesting Cost Optimization
1. Select "Cost Optimization" template
2. Fill in:
   - Service: "Cosmos DB"
   - Current cost: "$23/month (provisioned 400 RU/s)"
   - Optimization: "Switch to Serverless mode"
   - Savings: "$11-15/month (48-65% reduction)"
   - Trade-offs: "5-second cold start, lower throughput"
3. Submit → Auto-labeled `cost-optimization`, `enhancement`, `needs-triage`

### Improving Documentation
1. Select "Documentation Issue" template
2. Fill in:
   - Type: "README.md"
   - Issue: "Unclear - Documentation is confusing"
   - Location: "Quick Start section, line 92-110"
   - Problem: "Setup instructions skip Python virtual environment"
   - Suggestion: "Add section on creating venv before pip install"
3. Submit → Auto-labeled `documentation`, `needs-triage`

## Next Steps for Maintainers

### 1. Label Management
Ensure GitHub has these labels created:
- `bug`
- `enhancement`
- `documentation`
- `cost-optimization`
- `needs-triage`
- Phase labels: `phase-1`, `phase-2`, `phase-3`, `phase-4`, `phase-5`
- Component labels: `infrastructure`, `agent`, `api`, `observability`, etc.

### 2. Template Refinement
After initial usage, consider:
- Adding/removing fields based on what's actually useful
- Adjusting required vs optional fields
- Adding more dropdown options if patterns emerge

### 3. Automation
Consider GitHub Actions for:
- Auto-assigning based on component selection
- Auto-adding to project board
- Cost impact validation for Phase 4-5 features

### 4. Documentation
- Link to templates from README.md
- Mention in project blog post
- Show examples in contributor onboarding

## Benefits for Educational Project

1. **Quality:** Structured templates yield better bug reports and feature requests
2. **Organization:** Consistent categorization makes triage easier
3. **Learning:** Templates teach contributors what information matters
4. **Budget:** Cost template reinforces the $200/month constraint as core learning
5. **Community:** Lower barrier to entry with clear guidance
6. **Scalability:** Maintainers can handle more contributions efficiently

## Files Modified

1. **Created:** `.github/ISSUE_TEMPLATE/bug_report.yml`
2. **Created:** `.github/ISSUE_TEMPLATE/feature_request.yml`
3. **Created:** `.github/ISSUE_TEMPLATE/documentation.yml`
4. **Created:** `.github/ISSUE_TEMPLATE/cost_optimization.yml`
5. **Created:** `.github/ISSUE_TEMPLATE/config.yml`
6. **Enhanced:** `CONTRIBUTING.md` (added ~150 lines of new content)

## Testing

To test templates locally:
1. Push to GitHub
2. Navigate to repository → Issues → New Issue
3. Verify templates appear with proper formatting
4. Submit test issues to validate field behavior
5. Check labels are auto-applied correctly

## References

- [GitHub Issue Template Documentation](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)
- [GitHub Issue Form Schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [GitHub Issue Form Examples](https://github.com/github/docs/blob/main/.github/ISSUE_TEMPLATE/config.yml)

---

**Status:** ✅ Complete
**Ready for:** Push to GitHub and testing
**Recommendation:** Create 1-2 test issues to validate template behavior
