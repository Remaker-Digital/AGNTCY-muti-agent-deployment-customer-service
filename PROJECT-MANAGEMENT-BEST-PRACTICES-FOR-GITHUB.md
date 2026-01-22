# GitHub Project Management Best Practices

**Version**: 1.0  
**Last Updated**: January 2026  
**Purpose**: Standard practices for managing user stories and Kanban processes in GitHub development projects

---

## Table of Contents

1. [Overview](#overview)
2. [Recommended Tooling](#recommended-tooling)
3. [Issue Structure for User Stories](#issue-structure-for-user-stories)
4. [GitHub Projects Setup](#github-projects-setup)
5. [Kanban Board Configuration](#kanban-board-configuration)
6. [Workflow Automation](#workflow-automation)
7. [Branch Naming Conventions](#branch-naming-conventions)
8. [Labels and Classification](#labels-and-classification)
9. [Milestones and Sprints](#milestones-and-sprints)
10. [Best Practices Checklist](#best-practices-checklist)

---

## Overview

### Current Industry Standard (2025-2026)

**Primary Solution**: GitHub Projects + GitHub Issues  
**Enhancement**: ZenHub for advanced Agile/Scrum features

**Key Principles**:
- Keep developers in GitHub (minimize context switching)
- Use Issues as user stories
- Leverage automation to reduce manual updates
- Maintain clear visual workflow with Kanban boards
- Connect code commits directly to issues

---

## Recommended Tooling

### Option 1: GitHub Projects (Native) - RECOMMENDED FOR MOST TEAMS

**Use When**:
- Team size: 2-20 developers
- Simple to moderate workflow complexity
- Budget constraints
- Want native integration

**Capabilities**:
- Kanban board visualization
- Multi-repository support
- Custom fields and views
- Basic automation
- Direct issue/PR integration

**Limitations**:
- No native sprint planning
- No epic hierarchy
- Limited reporting (no burndown charts)
- Basic automation only

### Option 2: ZenHub - RECOMMENDED FOR AGILE TEAMS

**Use When**:
- Need full Scrum/Agile methodology
- Multi-repository projects
- Require sprint planning and velocity tracking
- Need epic hierarchy and roadmaps
- Want advanced reporting

**Capabilities**:
- Epic hierarchy (Projects → Epics → Issues → Sub-issues)
- Sprint planning with automation
- Multi-repo boards
- Burndown charts and velocity reports
- Planning poker for estimation
- Roadmap visualization

**Cost**: ~$8.33/user/month

### Other Options

- **Jira**: Enterprise-scale, complex workflows, steep learning curve
- **Shortcut**: Developer-friendly, story-based
- **Linear**: Modern interface, growing adoption
- **Taiga.io**: Open-source alternative

---

## Issue Structure for User Stories

### Issue Title Format

**DO**: Use clear, descriptive titles
```
Add OAuth2 authentication for Google login
Implement real-time chat notifications
Fix: User profile image upload fails on mobile
```

**DON'T**: Use user story format in title (hard to read in lists)
```
❌ As a user, I want to be able to log in with Google so that...
```

### Issue Description Template

```markdown
## User Story

As a [type of user]
I want [goal]
So that [benefit]

## Acceptance Criteria

- [ ] Criterion 1 with specific, testable outcome
- [ ] Criterion 2 with specific, testable outcome
- [ ] Criterion 3 with specific, testable outcome

## Technical Notes

- Implementation approach
- Dependencies
- API endpoints involved
- Database changes required

## Definition of Done

- [ ] Code complete and tested
- [ ] Code review approved
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Deployed to staging environment

## Story Points / Estimate

[2 points / 3 days] (if using estimation)
```

### Issue Metadata

**Required Fields**:
- **Labels**: Type, priority, component (see Labels section)
- **Assignee**: Developer(s) responsible
- **Milestone**: Sprint or release version
- **Project**: Add to relevant project board

**Optional Fields**:
- **Story Points**: For velocity tracking
- **Epic**: Link to parent epic (if using ZenHub)
- **Dependencies**: Link to blocking issues

---

## GitHub Projects Setup

### Step-by-Step Setup

1. **Create New Project**
   ```
   Repository → Projects tab → "New project"
   ```

2. **Choose Layout**
   - Select: **Board** (for Kanban)
   - Alternative: Table (for spreadsheet view), Roadmap (for timeline)

3. **Name Project**
   ```
   Examples:
   - "Product Backlog"
   - "Sprint 2024-Q1"
   - "[Product Name] Development"
   - "[Team Name] Kanban Board"
   ```

4. **Configure Views**
   - Create multiple views for different perspectives:
     - **Board View**: Daily workflow
     - **Table View**: Detailed planning
     - **Roadmap View**: Timeline visualization

5. **Add Repositories**
   - Link all relevant repositories to project
   - Issues from any linked repo can be added

### Project Configuration Best Practices

- **Access Control**: Set appropriate permissions (read/write/admin)
- **Default Fields**: Enable Status, Assignee, Labels, Milestone
- **Custom Fields**: Add Story Points, Sprint, Epic (if needed)
- **Saved Filters**: Create filters for common views (by assignee, label, etc.)

---

## Kanban Board Configuration

### Standard Column Structure

**Minimal (3 columns)**:
```
To Do → In Progress → Done
```

**Recommended (4-5 columns)**:
```
Backlog → To Do → In Progress → Review → Done
```

**Advanced (6+ columns)**:
```
Backlog → Ready → In Progress → Code Review → QA Testing → Staging → Done
```

### Column Definitions

| Column | Purpose | Entry Criteria | Exit Criteria |
|--------|---------|----------------|---------------|
| **Backlog** | Unrefined ideas, low priority | Created issue | Acceptance criteria defined |
| **To Do** | Ready for development | Acceptance criteria complete, assigned | Developer starts work |
| **In Progress** | Active development | Work started, branch created | PR opened |
| **Review** | Code review phase | PR submitted | PR approved |
| **QA/Testing** | Quality assurance | Review passed | Tests pass |
| **Done** | Completed work | Merged to main, deployed | - |

### Work-in-Progress (WIP) Limits

**Why**: Prevent bottlenecks, improve flow, reduce context switching

**How to Set**:
```
In Progress: 2-3 items per developer
Review: 3-5 items (team capacity)
```

**Note**: GitHub Projects supports visual WIP limit indicators but doesn't enforce them

### Column Automation Rules

Configure in Project Settings → Workflows:

```yaml
When issue status changes to "In Progress":
  - Assign to current user
  - Add label "in-development"

When PR is opened:
  - Move issue to "Review"
  - Add label "needs-review"

When PR is merged:
  - Move issue to "Done"
  - Add label "completed"
  - Close issue
```

---

## Workflow Automation

### Git Commit Automation

Use keywords in commit messages to auto-update issues:

**Close Issue**:
```bash
git commit -m "Add user authentication. Fixes #123"
git commit -m "Implement OAuth2. Closes #456"
git commit -m "Fix login bug. Resolves #789"
```

**Keywords that auto-close**: `fixes`, `closes`, `resolves` (and variations: fix, close, resolve, fixed, closed, resolved)

**Link Without Closing**:
```bash
git commit -m "Update auth flow for #123"
git commit -m "Partial implementation of #456"
```

### PR Automation

**PR Title Format**:
```
feat: Add Google OAuth2 authentication (#123)
fix: Resolve mobile upload issue (#456)
refactor: Improve error handling (#789)
```

**PR Description Template**:
```markdown
## Description
Brief summary of changes

## Related Issues
Closes #123
Relates to #456

## Testing
- [ ] Unit tests added
- [ ] Manual testing completed
- [ ] Edge cases covered

## Screenshots (if applicable)
[Add screenshots]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

### GitHub Actions Automation

**Example: Auto-label PRs**:
```yaml
name: Auto Label PR
on:
  pull_request:
    types: [opened]

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - name: Label based on branch
        uses: actions/labeler@v4
```

**Example: Move issues on PR merge**:
```yaml
name: Move to Done
on:
  pull_request:
    types: [closed]

jobs:
  move-card:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Move to Done column
        # Use GitHub API or third-party action
```

---

## Branch Naming Conventions

### Standard Format

```
<type>/<issue-number>-<short-description>

Examples:
feature/ISSUE-123-oauth-authentication
bugfix/ISSUE-456-mobile-upload-fix
refactor/ISSUE-789-error-handling
hotfix/ISSUE-101-security-patch
```

### Branch Types

| Type | Purpose | Base Branch | Merge To |
|------|---------|-------------|----------|
| `feature/` | New functionality | `develop` or `main` | `develop` |
| `bugfix/` | Bug fixes | `develop` or `main` | `develop` |
| `hotfix/` | Critical production fixes | `main` | `main` + `develop` |
| `refactor/` | Code improvements | `develop` | `develop` |
| `docs/` | Documentation only | `develop` or `main` | `develop` |
| `test/` | Test additions | `develop` | `develop` |

### Naming Rules

- **Use lowercase**: `feature/issue-123-...` not `Feature/Issue-123-...`
- **Use hyphens**: `user-authentication` not `user_authentication` or `userAuthentication`
- **Keep short**: 50 characters or less
- **Be descriptive**: Clear what the branch does
- **Include issue number**: Always reference the issue

### Complex Features (Multiple Issues)

```
Parent branch:
feature/PROJECT-123-payment-system

Child branches:
├── feature/ISSUE-457-stripe-integration
└── feature/ISSUE-458-payment-ui
```

---

## Labels and Classification

### Standard Label Categories

#### 1. Type Labels (What kind of work)
```
type: bug          - Red (#d73a4a)
type: feature      - Green (#0e8a16)
type: enhancement  - Blue (#0075ca)
type: documentation - Light blue (#0075ca)
type: refactor     - Yellow (#fbca04)
type: test         - Purple (#5319e7)
type: security     - Dark red (#b60205)
```

#### 2. Priority Labels (How urgent)
```
priority: critical  - Dark red (#b60205)
priority: high      - Orange (#d93f0b)
priority: medium    - Yellow (#fbca04)
priority: low       - Green (#0e8a16)
```

#### 3. Status Labels (Current state)
```
status: blocked     - Red (#d73a4a)
status: needs-review - Orange (#d93f0b)
status: ready       - Green (#0e8a16)
status: wip         - Yellow (#fbca04)
```

#### 4. Component Labels (What part of system)
```
component: api      - Light blue (#5EBEFF)
component: frontend - Purple (#D4C5F9)
component: backend  - Blue (#1D76DB)
component: database - Green (#BFD4F2)
component: auth     - Pink (#F9D0C4)
```

#### 5. Story Type Labels (Agile classification)
```
story: user-story  - Green (#0e8a16)
story: epic        - Purple (#5319e7)
story: task        - Blue (#0075ca)
story: spike       - Yellow (#fbca04)
```

### Label Usage Guidelines

**Required Labels** (every issue should have):
- At least one **type** label
- At least one **priority** label
- At least one **component** label

**Optional Labels**:
- Status labels (when needed)
- Story type (for Agile teams)

**Label Hygiene**:
- Remove stale labels when status changes
- Use consistent naming conventions
- Periodically audit and clean up unused labels
- Document custom labels in repository

---

## Milestones and Sprints

### Milestone Structure

**Release Milestones** (for release planning):
```
v1.0.0 - MVP Launch (Due: 2024-03-15)
v1.1.0 - Mobile Support (Due: 2024-04-30)
v2.0.0 - Major Redesign (Due: 2024-06-30)
```

**Sprint Milestones** (for Agile teams):
```
Sprint 1 - 2024-W03-W04 (Due: 2024-01-26)
Sprint 2 - 2024-W05-W06 (Due: 2024-02-09)
Sprint 3 - 2024-W07-W08 (Due: 2024-02-23)
```

### Milestone Best Practices

1. **Clear Due Dates**: Every milestone has a specific end date
2. **Description**: Include goals and success criteria
3. **Issue Assignment**: Assign issues during planning
4. **Progress Tracking**: Monitor completion percentage
5. **Close When Complete**: Close milestone when all issues are done

### Sprint Planning (ZenHub or Manual)

**Sprint Duration**: Typically 1-2 weeks

**Sprint Workflow**:
```
1. Sprint Planning
   - Review backlog
   - Select issues for sprint
   - Estimate story points
   - Assign to milestone

2. During Sprint
   - Daily standups
   - Move cards on board
   - Update issue status

3. Sprint Review
   - Demo completed work
   - Close completed issues
   - Review velocity

4. Sprint Retrospective
   - What went well
   - What needs improvement
   - Action items for next sprint
```

---

## Best Practices Checklist

### Initial Setup
- [ ] Create GitHub Project with Board layout
- [ ] Configure standard columns (minimum: To Do, In Progress, Review, Done)
- [ ] Set up standard labels (type, priority, component)
- [ ] Create milestones for releases/sprints
- [ ] Enable automation rules
- [ ] Document workflow in repository README

### Creating Issues
- [ ] Use clear, descriptive title
- [ ] Write user story in description (As a... I want... So that...)
- [ ] Define specific acceptance criteria
- [ ] Add appropriate labels (type, priority, component)
- [ ] Assign to milestone
- [ ] Add to project board
- [ ] Estimate story points (if using)
- [ ] Link to epic (if using ZenHub)

### During Development
- [ ] Create branch with issue number: `feature/ISSUE-123-description`
- [ ] Make small, focused commits
- [ ] Reference issue in commits: `#123`
- [ ] Move issue to "In Progress" when starting
- [ ] Update issue with progress notes
- [ ] Keep WIP within limits

### Pull Requests
- [ ] Title includes issue number: `feat: Description (#123)`
- [ ] Description links to issue: `Closes #123`
- [ ] Includes testing notes
- [ ] Passes all CI checks
- [ ] Requested reviewers assigned
- [ ] Move issue to "Review" column

### Completion
- [ ] PR reviewed and approved
- [ ] All conversations resolved
- [ ] Merge with keyword: `Closes #123`
- [ ] Issue automatically moved to "Done"
- [ ] Deployed to staging/production
- [ ] Milestone updated

### Team Hygiene
- [ ] Daily standup using board as visual aid
- [ ] Weekly backlog grooming
- [ ] Regular label and milestone cleanup
- [ ] Update board state in real-time
- [ ] Archive completed milestones
- [ ] Review and refine workflow quarterly

---

## Common Anti-Patterns to Avoid

### ❌ DON'T

1. **Large, vague issues**
   - Bad: "Improve authentication"
   - Good: "Add 2FA support for email/password login"

2. **No acceptance criteria**
   - Always define testable acceptance criteria

3. **Stale issues**
   - Close or archive issues older than 6 months if not relevant

4. **Too many columns**
   - More than 7 columns creates confusion
   - Keep it simple, add complexity only if needed

5. **Manual status updates**
   - Use automation whenever possible

6. **Mixing concerns**
   - Don't put bugs and features in same milestone without clear prioritization

7. **No issue-branch linking**
   - Always reference issue number in branch name and commits

8. **Bypassing the board**
   - All work should go through the Kanban board
   - Don't work on issues not on the board

---

## Integration with CI/CD

### GitHub Actions Integration

```yaml
# .github/workflows/issue-management.yml
name: Issue Management
on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, closed]

jobs:
  manage-issues:
    runs-on: ubuntu-latest
    steps:
      - name: Add to project
        uses: actions/add-to-project@v0.4.0
        with:
          project-url: https://github.com/orgs/ORG/projects/1
          github-token: ${{ secrets.ADD_TO_PROJECT_PAT }}
```

### Status Check Requirements

Require these checks before merging:
- [ ] All tests pass
- [ ] Code coverage meets threshold
- [ ] Linting passes
- [ ] Security scan passes
- [ ] At least one approval

---

## Templates for Quick Start

### Issue Template (`.github/ISSUE_TEMPLATE/user-story.md`)

```markdown
---
name: User Story
about: Create a new user story
title: ''
labels: 'story: user-story'
assignees: ''
---

## User Story

As a [type of user]
I want [goal]
So that [benefit]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes

[Implementation details]

## Definition of Done

- [ ] Code complete and tested
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Deployed to staging
```

### Pull Request Template (`.github/pull_request_template.md`)

```markdown
## Description
[Brief description of changes]

## Related Issues
Closes #

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings generated
```

---

## Tools and Resources

### Essential Browser Extensions
- **ZenHub**: Full Agile project management
- **Refined GitHub**: UI enhancements
- **Octotree**: Code tree navigation

### Recommended Reading
- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [Agile User Story Best Practices](https://www.atlassian.com/agile/project-management/user-stories)
- [Kanban Guide](https://www.atlassian.com/agile/kanban)

### API Access
- **GitHub GraphQL API**: For custom automation
- **GitHub REST API**: For integrations
- **ZenHub API**: For advanced reporting

---

## Troubleshooting

### Common Issues

**Issue: Board not updating automatically**
- Check automation rules are enabled
- Verify keyword usage in commits
- Ensure issues are properly linked to project

**Issue: Too many issues in "In Progress"**
- Implement WIP limits
- Review and close stale issues
- Improve issue sizing (break down large issues)

**Issue: Difficulty tracking cross-repo work**
- Use ZenHub for multi-repo boards
- Create organization-level project
- Use consistent labeling across repos

**Issue: Team not using the board**
- Make board part of daily standup
- Gamify with metrics and recognition
- Ensure board is easily accessible
- Simplify workflow if too complex

---

## Metrics to Track

### Velocity Metrics (Agile/Scrum)
- Story points completed per sprint
- Burndown rate
- Velocity trend over time

### Cycle Time Metrics
- Time from "To Do" to "Done"
- Time in "Review" state
- Time to first review

### Quality Metrics
- Issues reopened
- Bugs per feature
- Code review iterations

### Team Health Metrics
- WIP limits adherence
- Issue age (avoid stale issues)
- Milestone completion rate

---

## Version History

- **v1.0 (January 2026)**: Initial document created based on 2025-2026 industry standards

---

## Quick Reference Card

```
ISSUE NAMING:     Clear, descriptive titles
BRANCH FORMAT:    <type>/ISSUE-<num>-<description>
COMMIT KEYWORDS:  fixes, closes, resolves
PR FORMAT:        <type>: Description (#123)
LABELS:           type + priority + component (minimum)
COLUMNS:          To Do → In Progress → Review → Done
AUTOMATION:       Enable for PR/merge actions
WIP LIMITS:       2-3 items per developer
MILESTONES:       Use for sprints/releases
REFINEMENT:       Weekly backlog grooming
```

---

**Document Maintained By**: Development Team  
**Last Review**: January 2026  
**Next Review**: July 2026
