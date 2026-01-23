# How to Publish Architecture Document to GitHub Wiki

**Document:** `docs/WIKI-Architecture.md`
**Destination:** GitHub Wiki (https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki)

---

## Quick Start (Recommended Method)

### Option 1: Web Interface (Easiest)

1. **Navigate to Wiki:**
   - Go to: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki
   - Click "New Page" button

2. **Create Architecture Page:**
   - Title: `Architecture`
   - Copy content from `docs/WIKI-Architecture.md`
   - Paste into wiki editor
   - Click "Save Page"

3. **Set as Home (Optional):**
   - If you want Architecture to be the wiki home page:
   - Go to wiki settings
   - Set "Home page" to `Architecture`

**Time:** ~2 minutes

---

### Option 2: Git Clone (For Maintenance)

GitHub wikis are actually separate Git repositories. You can clone and manage them like code:

#### Step 1: Clone the Wiki Repository

```bash
# Navigate to a directory where you want to clone the wiki
cd C:\Users\micha\OneDrive\Desktop

# Clone the wiki repo (note .wiki.git suffix)
git clone https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service.wiki.git

# Navigate into wiki repo
cd AGNTCY-muti-agent-deployment-customer-service.wiki
```

#### Step 2: Copy Architecture Document

```bash
# Copy the architecture document from main repo
cp ../AGNTCY-muti-agent-deployment-customer-service/docs/WIKI-Architecture.md Architecture.md

# Add to git
git add Architecture.md

# Commit
git commit -m "Add comprehensive system architecture documentation"

# Push to wiki
git push origin master
```

#### Step 3: Verify

- Visit: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Architecture
- Confirm the page displays correctly

**Time:** ~5 minutes

---

## Wiki Maintenance

### Updating the Architecture Document

**When to Update:**
- After completing each phase (Phase 2, 3, 4, 5)
- When making significant architectural changes
- When adding new agents or services
- When budget/cost estimates change

**How to Update:**

**Option A: Web Interface**
1. Edit `docs/WIKI-Architecture.md` in main repo
2. Commit changes to main repo
3. Navigate to wiki page
4. Click "Edit" button
5. Copy updated content from `docs/WIKI-Architecture.md`
6. Paste and save

**Option B: Git Clone**
1. Edit `docs/WIKI-Architecture.md` in main repo
2. Commit to main repo
3. In wiki clone directory:
   ```bash
   cd AGNTCY-muti-agent-deployment-customer-service.wiki

   # Copy updated file
   cp ../AGNTCY-muti-agent-deployment-customer-service/docs/WIKI-Architecture.md Architecture.md

   # Commit and push
   git add Architecture.md
   git commit -m "Update architecture: [describe changes]"
   git push origin master
   ```

---

### Creating Additional Wiki Pages

The architecture document references several other potential wiki pages. Consider creating these:

#### 1. Getting Started (Quick start guide)
**Content:** Installation, local setup, first run
**Filename:** `Getting-Started.md`

#### 2. Agent Development Guide
**Content:** How to create new agents, AGNTCY SDK patterns
**Filename:** `Agent-Development.md`

#### 3. Deployment Guide
**Content:** Azure deployment steps, Terraform usage
**Filename:** `Deployment.md`

#### 4. Troubleshooting
**Content:** Common issues, debugging tips
**Filename:** `Troubleshooting.md`

#### 5. API Reference
**Content:** Agent API specs, message formats
**Filename:** `API-Reference.md`

**To create any of these:**
1. Create markdown file in wiki repo (or via web interface)
2. Follow same process as Architecture page

---

## Wiki Structure Recommendations

### Sidebar Navigation (Create `_Sidebar.md`)

```markdown
### Documentation

- [Home](Home)
- [Architecture](Architecture)
- [Getting Started](Getting-Started)
- [Agent Development](Agent-Development)
- [Deployment](Deployment)
- [API Reference](API-Reference)
- [Troubleshooting](Troubleshooting)

### Project Management

- [User Stories](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/user-stories-phased.md)
- [GitHub Project Board](https://github.com/orgs/Remaker-Digital/projects/1)
- [Milestones](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/milestones)

### Resources

- [AGNTCY SDK Docs](https://docs.agntcy.com)
- [Azure Architecture Center](https://learn.microsoft.com/azure/architecture/)
- [PROJECT-README.txt](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/PROJECT-README.txt)
```

**To add sidebar:**
1. Create file `_Sidebar.md` in wiki repo
2. Copy content above
3. Commit and push (or create via web interface)

---

### Footer (Create `_Footer.md`)

```markdown
---

**Project:** [AGNTCY Multi-Agent Customer Service Platform](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service)
**License:** Public (Educational Use)
**Last Updated:** 2026-01-22

[Report Issue](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues) | [Discussions](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/discussions) | [Contributing](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/CONTRIBUTING.md)
```

**To add footer:**
1. Create file `_Footer.md` in wiki repo
2. Copy content above
3. Commit and push (or create via web interface)

---

## Version Control Best Practices

### Keep Wiki in Sync with Main Repo

**Workflow:**

1. **Main Repo (`docs/WIKI-Architecture.md`):**
   - Source of truth
   - Update as part of normal development
   - Commit with descriptive messages

2. **Wiki Repo (`Architecture.md`):**
   - Published copy
   - Update after main repo changes
   - Keep synchronized weekly or after major changes

**Why This Approach:**
- Wiki is readable on GitHub (better discoverability)
- `docs/` folder has version history and PR review process
- Wiki can be updated independently for typos/formatting
- Both locations benefit users (developers use docs/, general readers use wiki)

---

## Automation (Optional - Post Phase 5)

### GitHub Actions to Auto-Sync

Create `.github/workflows/sync-wiki.yml` in main repo:

```yaml
name: Sync Wiki

on:
  push:
    paths:
      - 'docs/WIKI-Architecture.md'
    branches:
      - main

jobs:
  sync-wiki:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main repo
        uses: actions/checkout@v3

      - name: Checkout wiki repo
        uses: actions/checkout@v3
        with:
          repository: ${{ github.repository }}.wiki
          path: wiki

      - name: Copy architecture doc
        run: |
          cp docs/WIKI-Architecture.md wiki/Architecture.md

      - name: Commit and push to wiki
        run: |
          cd wiki
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add Architecture.md
          git commit -m "Auto-sync: Update architecture from main repo"
          git push
```

**Note:** This requires GitHub Actions to have write access to wiki repository.

---

## Troubleshooting

### Issue: "Wiki not enabled"
**Solution:** Enable wiki in repository settings:
1. Go to repository settings
2. Scroll to "Features"
3. Check "Wikis"

### Issue: "Permission denied when pushing to wiki"
**Solution:** Ensure you have write access to repository

### Issue: "Images not displaying"
**Solution:**
- Upload images to wiki via web interface (uploads to `wiki/uploads/`)
- Reference with: `![Description](uploads/image.png)`
- Or use absolute URLs from main repo: `![Description](https://raw.githubusercontent.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/main/docs/images/diagram.png)`

### Issue: "Links broken in wiki"
**Solution:**
- Wiki uses different link format than GitHub markdown
- Relative links work: `[Data Requirements](Data-Staleness-Requirements)`
- External links: `[Main Repo](https://github.com/...)`

---

## Checklist

**Before Publishing:**
- [ ] Review `docs/WIKI-Architecture.md` for accuracy
- [ ] Check all internal links work
- [ ] Verify external references are correct
- [ ] Ensure no sensitive information (API keys, credentials)
- [ ] Confirm diagrams render correctly (if using mermaid/ASCII)

**After Publishing:**
- [ ] Test all links in published wiki page
- [ ] Verify navigation (sidebar if created)
- [ ] Check formatting on GitHub wiki (may differ from markdown preview)
- [ ] Add link to Architecture page from repository README.md

**Ongoing Maintenance:**
- [ ] Update after each phase completion
- [ ] Review quarterly for accuracy
- [ ] Solicit feedback via GitHub issues
- [ ] Keep in sync with `docs/WIKI-Architecture.md` changes

---

## Quick Reference Commands

```bash
# Clone wiki repo
git clone https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service.wiki.git

# Update architecture page
cd AGNTCY-muti-agent-deployment-customer-service.wiki
cp ../AGNTCY-muti-agent-deployment-customer-service/docs/WIKI-Architecture.md Architecture.md
git add Architecture.md
git commit -m "Update architecture documentation"
git push origin master

# View wiki
open https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/wiki/Architecture
```

---

## Support

**Questions?**
- Open an issue: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues
- Start a discussion: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/discussions

**Document Issues:**
If you find errors in the architecture documentation, please:
1. Open an issue in main repo
2. Tag with `documentation` label
3. Reference the section that needs correction

---

**Created:** 2026-01-22
**Last Updated:** 2026-01-22
**Maintained By:** Project contributors
