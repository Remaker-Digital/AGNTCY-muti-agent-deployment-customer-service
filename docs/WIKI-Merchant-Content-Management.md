# Merchant Content Management for RAG

This guide explains how merchants load, vectorize, and optimize content for the Retrieval-Augmented Generation (RAG) system in the AGNTCY Multi-Agent Customer Service platform.

---

## Overview

The RAG system enables the AI assistant to answer customer questions by retrieving relevant information from your knowledge base. This includes:

- **Product documentation** - Specifications, features, usage guides
- **Company policies** - Returns, shipping, privacy, terms of service
- **FAQs and troubleshooting** - Common questions and solutions
- **Support articles** - How-to guides, tutorials, best practices

### How RAG Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG Content Pipeline                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │  Merchant   │───►│  Content    │───►│  Vector     │───►│  Cosmos DB  │ │
│   │  Content    │    │  Processor  │    │  Embeddings │    │  Storage    │ │
│   │  (Markdown) │    │  (CLI Tool) │    │  (Azure AI) │    │  (Search)   │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                              │
│   At Query Time:                                                            │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │  Customer   │───►│  Query      │───►│  Vector     │───►│  AI Agent   │ │
│   │  Question   │    │  Embedding  │    │  Search     │    │  Response   │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Content Structure

### Supported Content Types

| Content Type | Format | Location | Update Frequency |
|--------------|--------|----------|------------------|
| Policies | Markdown or JSON | `content/policies/` | Monthly or as needed |
| Products | JSON (auto-synced from Shopify) | Shopify API | Real-time |
| FAQs | Markdown | `content/faqs/` | Weekly |
| Troubleshooting | Markdown | `content/troubleshooting/` | As issues arise |
| Support Articles | Markdown | `content/articles/` | Weekly |

### Directory Structure

```
content/
├── policies/
│   ├── return-policy.md
│   ├── shipping-policy.md
│   ├── privacy-policy.md
│   └── terms-of-service.md
├── faqs/
│   ├── ordering.md
│   ├── payments.md
│   ├── account.md
│   └── products.md
├── troubleshooting/
│   ├── brewing-issues.md
│   ├── equipment-care.md
│   └── subscription-problems.md
├── articles/
│   ├── getting-started.md
│   ├── brewing-guide.md
│   └── coffee-storage.md
└── metadata.yaml           # Content configuration
```

---

## Content Format

### Markdown with Frontmatter

All merchant content uses Markdown with YAML frontmatter for metadata:

```markdown
---
title: "Return Policy"
category: policy
keywords:
  - return
  - refund
  - exchange
  - money back
last_updated: 2026-01-28
effective_date: 2026-01-01
version: 2.1
---

# Return Policy

## Overview

We offer a 30-day satisfaction guarantee on all purchases...

## Eligibility

To be eligible for a return, items must be:
- Unused and in original packaging
- Purchased within the last 30 days
- Accompanied by proof of purchase

## Process

1. Contact customer support at support@example.com
2. Receive a Return Merchandise Authorization (RMA) number
3. Ship the item back within 14 days
4. Refund processed within 5-7 business days

## Exceptions

The following items are not eligible for return:
- Opened coffee bags (for hygiene reasons)
- Personalized or custom items
- Gift cards

## Contact

For questions about returns, contact us at:
- Email: support@example.com
- Phone: 1-800-COFFEE
- Chat: Available 9am-5pm EST
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display title for the document |
| `category` | Yes | One of: `policy`, `faq`, `troubleshooting`, `article`, `product` |
| `keywords` | Yes | List of search terms (improves retrieval accuracy) |
| `last_updated` | Yes | ISO date of last content update |
| `effective_date` | No | When the policy becomes effective |
| `version` | No | Document version for tracking changes |
| `language` | No | Content language (default: `en-US`) |
| `audience` | No | Target audience: `customer`, `prospect`, `all` |

---

## Content Ingestion Tool

### Installation

The content management CLI is included in the project:

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m scripts.content_manager --help
```

### Commands

#### 1. Validate Content

Check content for formatting issues before ingestion:

```bash
python -m scripts.content_manager validate content/

# Output:
# ✓ policies/return-policy.md - Valid
# ✓ policies/shipping-policy.md - Valid
# ✗ faqs/ordering.md - Missing required field: keywords
#
# Summary: 2 valid, 1 error
```

#### 2. Preview Chunks

See how content will be split for vectorization:

```bash
python -m scripts.content_manager preview content/policies/return-policy.md

# Output:
# Document: Return Policy
# Chunks: 4
#
# Chunk 1 (Overview): 156 tokens
# "We offer a 30-day satisfaction guarantee..."
#
# Chunk 2 (Eligibility): 89 tokens
# "To be eligible for a return, items must be..."
#
# Chunk 3 (Process): 112 tokens
# "1. Contact customer support at..."
#
# Chunk 4 (Exceptions): 78 tokens
# "The following items are not eligible..."
```

#### 3. Ingest Content

Process and vectorize content:

```bash
# Dry run (shows what would be processed)
python -m scripts.content_manager ingest content/ --dry-run

# Full ingestion
python -m scripts.content_manager ingest content/

# Ingest specific category
python -m scripts.content_manager ingest content/policies/

# Force re-vectorization (even if unchanged)
python -m scripts.content_manager ingest content/ --force
```

#### 4. Check Status

View current knowledge base status:

```bash
python -m scripts.content_manager status

# Output:
# Knowledge Base Status
# ─────────────────────
# Total Documents: 75
# Total Chunks: 312
# Total Tokens: ~45,000
#
# By Category:
# - Policies: 5 documents, 24 chunks
# - FAQs: 15 documents, 67 chunks
# - Troubleshooting: 10 documents, 45 chunks
# - Articles: 10 documents, 52 chunks
# - Products: 35 documents (synced from Shopify)
#
# Last Sync: 2026-01-28 14:32:00 UTC
# Vector Index: Healthy
```

#### 5. Test Retrieval

Test how well content retrieves for sample queries:

```bash
python -m scripts.content_manager test-query "How do I return a product?"

# Output:
# Query: "How do I return a product?"
#
# Top 3 Results:
# 1. [Score: 0.94] Return Policy - Process
#    "1. Contact customer support at support@example.com..."
#
# 2. [Score: 0.87] Return Policy - Eligibility
#    "To be eligible for a return, items must be..."
#
# 3. [Score: 0.72] FAQ - Ordering - Can I change my order?
#    "If you need to modify or cancel your order..."
```

---

## Vectorization Process

### How Documents Are Processed

1. **Parse**: Extract content and metadata from Markdown
2. **Chunk**: Split into semantic sections (by headers)
3. **Enrich**: Add keywords and metadata to each chunk
4. **Embed**: Generate vector embeddings via Azure OpenAI
5. **Index**: Store in Cosmos DB with vector search index

### Chunking Strategy

Documents are split by **semantic boundaries** (headers) rather than fixed character counts:

```
┌─────────────────────────────────────────────────────────────────┐
│  Original Document                                               │
├─────────────────────────────────────────────────────────────────┤
│  # Return Policy                                                │
│                                                                  │
│  ## Overview                                                     │
│  We offer a 30-day satisfaction guarantee...                    │
│                                                                  │
│  ## Eligibility                    ─────► Chunk 1 (Overview)    │
│  To be eligible for a return...                                 │
│                                    ─────► Chunk 2 (Eligibility) │
│  ## Process                                                      │
│  1. Contact customer support...    ─────► Chunk 3 (Process)     │
│                                                                  │
│  ## Exceptions                                                   │
│  The following items...            ─────► Chunk 4 (Exceptions)  │
└─────────────────────────────────────────────────────────────────┘
```

### Embedding Model

| Setting | Value | Rationale |
|---------|-------|-----------|
| Model | `text-embedding-3-large` | Best accuracy for semantic search |
| Dimensions | 1536 | Industry standard, good accuracy/cost balance |
| Cost | ~$0.13 per 1M tokens | ~$0.26/month for 75-doc knowledge base |

---

## Optimization Best Practices

### 1. Write Clear, Specific Titles

Titles heavily influence retrieval accuracy:

```markdown
# ❌ Bad: Policy
# ❌ Bad: Returns
# ✓ Good: Return and Refund Policy
# ✓ Good: 30-Day Money-Back Guarantee Policy
```

### 2. Use Descriptive Section Headers

Section headers become chunk titles:

```markdown
## ❌ Bad: Section 1
## ❌ Bad: Info
## ✓ Good: How to Request a Return
## ✓ Good: Return Eligibility Requirements
```

### 3. Include Comprehensive Keywords

Keywords improve hybrid search (vector + keyword matching):

```yaml
# ❌ Bad: Limited keywords
keywords:
  - return

# ✓ Good: Comprehensive keywords
keywords:
  - return
  - refund
  - exchange
  - money back
  - send back
  - return policy
  - return shipping
  - restocking fee
```

### 4. Keep Sections Focused

Each section should address ONE topic:

```markdown
## ❌ Bad: Everything in one section
All returns must be made within 30 days. We ship via USPS.
Contact us at support@example.com for loyalty points.

## ✓ Good: Focused sections
## Return Window
Returns must be made within 30 days of purchase.

## Return Shipping
We provide prepaid USPS return labels.

## Loyalty Points on Returns
Loyalty points will be deducted when returns are processed.
```

### 5. Optimize Chunk Size

Aim for 100-500 tokens per chunk (roughly 75-375 words):

| Chunk Size | Result |
|------------|--------|
| < 50 tokens | Too small, lacks context |
| 100-500 tokens | Optimal for retrieval |
| > 1000 tokens | Too large, dilutes relevance |

### 6. Add Quick Answers

Include summary answers that can be returned directly:

```markdown
## Quick Answer

**Can I return opened coffee bags?**
No, opened coffee bags cannot be returned for hygiene reasons.
Unopened bags can be returned within 30 days.
```

### 7. Update Regularly

Stale content reduces trust and accuracy:

| Content Type | Recommended Update Frequency |
|--------------|------------------------------|
| Policies | Quarterly or when changed |
| FAQs | Monthly |
| Troubleshooting | As issues are resolved |
| Products | Real-time (via Shopify sync) |

---

## Testing and Validation

### Retrieval Quality Metrics

After ingesting content, validate retrieval quality:

```bash
# Run full test suite
python -m scripts.content_manager test-suite

# Output:
# Running retrieval tests...
#
# Policy Queries: 20/20 passed (100%)
# FAQ Queries: 18/20 passed (90%)
# Troubleshooting Queries: 9/10 passed (90%)
#
# Overall Retrieval@3: 94%
# Target: >90% ✓
```

### Common Issues and Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| Low retrieval score | Relevant doc not in top 3 | Add more keywords, improve title |
| Wrong doc retrieved | Unrelated content ranked first | Split ambiguous sections, add specificity |
| Partial matches | Only part of answer retrieved | Combine related sections |
| Stale content | Outdated info returned | Update `last_updated`, re-ingest |

### A/B Testing Content Changes

Test content changes before deploying:

```bash
# Compare current vs proposed content
python -m scripts.content_manager compare \
  --current content/policies/return-policy.md \
  --proposed content/policies/return-policy-v2.md \
  --queries test-data/return-queries.json

# Output:
# Query: "How long do I have to return?"
# - Current: Score 0.89, Chunk: "Return Window"
# - Proposed: Score 0.94, Chunk: "30-Day Return Window" (+0.05)
#
# Query: "Can I exchange instead of return?"
# - Current: Score 0.72, Chunk: "Process"
# - Proposed: Score 0.91, Chunk: "Exchanges and Replacements" (+0.19)
#
# Overall: Proposed version improves retrieval by +8.2%
```

---

## Content Sync and Updates

### Automatic Sync (Products)

Product information syncs automatically from Shopify:

```
┌────────────────┐     Webhook      ┌────────────────┐
│  Shopify       │ ──────────────►  │  Event Handler │
│  (Products)    │                  │  (NATS)        │
└────────────────┘                  └───────┬────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  Re-vectorize  │
                                   │  Product Doc   │
                                   └────────────────┘
```

### Manual Sync (Policies, FAQs)

For manually-managed content:

```bash
# Watch for file changes and auto-sync
python -m scripts.content_manager watch content/

# Or sync on-demand
python -m scripts.content_manager sync content/
```

### Sync Schedule

| Content Type | Sync Method | Frequency |
|--------------|-------------|-----------|
| Products | Shopify webhook | Real-time |
| Policies | Manual or watch | On change |
| FAQs | Manual or watch | On change |
| Articles | Manual or watch | On change |

---

## Cost Considerations

### Embedding Costs

| Operation | Cost | Notes |
|-----------|------|-------|
| Initial ingestion (75 docs) | ~$0.01 | One-time |
| Re-vectorize single doc | ~$0.0001 | Per update |
| Monthly maintenance | ~$0.26 | Incremental updates |
| Query embeddings | ~$0.13/1M tokens | Included in query cost |

### Storage Costs

| Component | Monthly Cost |
|-----------|--------------|
| Cosmos DB (vectors) | ~$5-10 |
| Blob Storage (source files) | ~$1-2 |
| **Total** | ~$6-12/month |

### Optimization Tips

1. **Batch updates**: Ingest multiple docs at once to reduce API calls
2. **Skip unchanged**: Use `--skip-unchanged` flag to avoid re-vectorizing
3. **Monitor usage**: Check Azure OpenAI usage dashboard weekly

---

## Troubleshooting

### Content Not Appearing in Search

1. Verify content was ingested:
   ```bash
   python -m scripts.content_manager status | grep "your-doc-name"
   ```

2. Check for validation errors:
   ```bash
   python -m scripts.content_manager validate content/your-doc.md
   ```

3. Re-ingest with force flag:
   ```bash
   python -m scripts.content_manager ingest content/your-doc.md --force
   ```

### Low Retrieval Scores

1. Test specific queries:
   ```bash
   python -m scripts.content_manager test-query "your query"
   ```

2. Review chunk boundaries:
   ```bash
   python -m scripts.content_manager preview content/your-doc.md
   ```

3. Add more keywords to frontmatter

### Sync Failures

1. Check Azure OpenAI connectivity:
   ```bash
   python -m scripts.content_manager health-check
   ```

2. Verify Cosmos DB connection:
   ```bash
   python -m scripts.content_manager health-check --component cosmos
   ```

3. Review error logs:
   ```bash
   tail -f logs/content-manager.log
   ```

---

## Security Considerations

### PII in Content

- **DO NOT** include customer PII in knowledge base content
- Use placeholder examples: "John D." instead of real names
- Product documentation should use generic examples

### Access Control

| Role | Permissions |
|------|-------------|
| Merchant Admin | Full content management |
| Content Editor | Add/edit content, no delete |
| Viewer | Read-only access |

### Audit Trail

All content changes are logged:

```bash
python -m scripts.content_manager audit-log --days 30

# Output:
# 2026-01-28 14:32:00 | admin@store.com | CREATE | policies/return-policy.md
# 2026-01-27 09:15:00 | editor@store.com | UPDATE | faqs/ordering.md
# 2026-01-26 16:45:00 | admin@store.com | DELETE | articles/old-guide.md
```

---

## Related Documentation

- [[Architecture|Architecture]] - System architecture overview
- [[Model Context Protocol|Model-Context-Protocol]] - MCP integration details
- [[Scalability|Scalability]] - Auto-scaling and performance
- [[UCP Integration Guide|UCP-Integration-Guide]] - Commerce protocol integration

---

## Quick Reference

### Commands Cheat Sheet

```bash
# Validate all content
python -m scripts.content_manager validate content/

# Preview chunking
python -m scripts.content_manager preview content/doc.md

# Ingest content
python -m scripts.content_manager ingest content/

# Check status
python -m scripts.content_manager status

# Test a query
python -m scripts.content_manager test-query "your question"

# Run full test suite
python -m scripts.content_manager test-suite

# Watch for changes
python -m scripts.content_manager watch content/
```

### Content Template

```markdown
---
title: "Your Document Title"
category: policy|faq|troubleshooting|article
keywords:
  - keyword1
  - keyword2
  - keyword3
last_updated: 2026-01-28
---

# Your Document Title

## Overview

Brief introduction to the topic.

## Section 1

Detailed content for section 1.

## Section 2

Detailed content for section 2.

## Quick Answer

**Common Question?**
Direct answer to the most common question about this topic.
```

---

*Last Updated: 2026-01-28*
