# IMPLEMENTATION DOCUMENTATION

**Last Updated**: 2025-11-06
**Purpose**: Detailed implementation guides for all system components

---

## 📁 STRUCTURE

```
docs/
├── QUICK-REFERENCE.md          # 1-page printable reference card
└── implementation/
    ├── README.md               # This file
    ├── roadmap.md              # Week-by-week implementation plan
    ├── ai-system.md            # AI components deep dive (FaceID, Voice, etc.)
    ├── backend-modules.md      # Backend modules status & gaps
    ├── technical-debt.md       # Architecture violations & fixes
    ├── frontend.md             # Frontend apps (Kiosk, Admin) - TODO
    ├── crm-messaging.md        # CRM & Messaging (Zalo OA, SMS, Email) - TODO
    └── modules/                # Individual module docs - TODO
        ├── orders.md
        ├── payments.md
        ├── promotions.md
        └── ...
```

---

## 📖 HOW TO USE

### For Developers

**Starting a New Task?**
1. Check [MASTER-STATUS.md](../../MASTER-STATUS.md) for current phase
2. Check [QUICK-REFERENCE.md](../QUICK-REFERENCE.md) for this week's todos
3. Read relevant detailed doc (roadmap, ai-system, backend-modules, etc.)
4. Implement feature
5. Update compliance % in MASTER-STATUS.md

**Example Workflow**:
```bash
# Week 1 Day 1: Fix idempotency bug

# 1. Check status
cat MASTER-STATUS.md | grep "idempotency"

# 2. Read detailed guide
cat docs/implementation/technical-debt.md | grep -A 30 "Idempotency Bug"

# 3. Read quick reference
cat docs/QUICK-REFERENCE.md

# 4. Implement fix
vim apps/api/src/orders/orders.service.ts

# 5. Test
pnpm test orders.service.spec.ts

# 6. Commit
git commit -m "fix(orders): integrate idempotency service"

# 7. Update status
vim MASTER-STATUS.md  # Update checklist
```

---

### For Project Managers

**Weekly Review**:
1. Check [MASTER-STATUS.md](../../MASTER-STATUS.md) - Executive Summary
2. Review [QUICK-REFERENCE.md](../QUICK-REFERENCE.md) - Current sprint status
3. Check compliance dashboard
4. Identify blockers
5. Plan next week

**Monthly Planning**:
1. Review [roadmap.md](roadmap.md) - Phase progress
2. Check resource requirements
3. Review risk register
4. Adjust timeline if needed

---

### For Stakeholders

**Quick Update (5 min)**:
- Read [MASTER-STATUS.md](../../MASTER-STATUS.md) - Executive Summary only
- Key numbers: Compliance %, Timeline, Critical actions

**Deep Dive (30 min)**:
- Read specific section in detailed docs
- Example: [ai-system.md](ai-system.md) for AI features status

---

## 📚 DOCUMENT DESCRIPTIONS

### MASTER-STATUS.md (Main Dashboard)
- **Length**: 150-200 lines
- **Read Time**: 5-10 minutes
- **Update Frequency**: Weekly
- **Purpose**: Single Source of Truth, quick overview
- **Audience**: Everyone (developers, PMs, stakeholders)

### QUICK-REFERENCE.md (1-Page Card)
- **Length**: 1 page
- **Read Time**: 2 minutes
- **Update Frequency**: Weekly (start of sprint)
- **Purpose**: Current sprint focus, printable
- **Audience**: Developers (daily reference)

### roadmap.md (Phase-by-Phase Plan)
- **Length**: ~500 lines
- **Read Time**: 30 minutes
- **Update Frequency**: Monthly (or after phase completion)
- **Purpose**: Week-by-week implementation guide
- **Audience**: Developers, PMs

### ai-system.md (AI Deep Dive)
- **Length**: ~600 lines
- **Read Time**: 45 minutes
- **Update Frequency**: As AI features progress
- **Purpose**: Technical specs for 7 AI components
- **Audience**: ML engineers, backend developers

### backend-modules.md (Module Status)
- **Length**: ~500 lines
- **Read Time**: 30 minutes
- **Update Frequency**: Weekly
- **Purpose**: Track module completion, gaps, priorities
- **Audience**: Backend developers

### technical-debt.md (Architecture & Debt)
- **Length**: ~400 lines
- **Read Time**: 30 minutes
- **Update Frequency**: As issues discovered/fixed
- **Purpose**: Track technical debt, architecture violations
- **Audience**: Developers, Tech Leads

---

## 🔄 UPDATE WORKFLOW

### Weekly Updates (Every Monday)

**Step 1**: Update current phase status
```bash
vim MASTER-STATUS.md
# Update: Current sprint, compliance %, blockers
```

**Step 2**: Update quick reference
```bash
vim docs/QUICK-REFERENCE.md
# Update: This week todos, completed tasks
```

**Step 3**: Update relevant detailed doc
```bash
# If working on AI features
vim docs/implementation/ai-system.md

# If working on backend modules
vim docs/implementation/backend-modules.md
```

### Phase Completion Updates

**Step 1**: Update roadmap
```bash
vim docs/implementation/roadmap.md
# Mark phase as completed, update next phase
```

**Step 2**: Update compliance %
```bash
vim MASTER-STATUS.md
# Update compliance dashboard table
```

**Step 3**: Commit with summary
```bash
git add docs/
git commit -m "docs: update status after Phase 0 completion

- Fixed idempotency bug
- Added observability (Winston + Prometheus)
- Integrated OpenAPI
- Test coverage: 0% -> 25%
- Compliance: 20% -> 22%
"
```

---

## 🎯 PRINCIPLES

### 1. Single Source of Truth
- **MASTER-STATUS.md** is the authority
- All other docs link to it
- Never duplicate information

### 2. Layered Detail
- **Executive Summary**: 60 seconds
- **Quick Reference**: 2 minutes
- **Main Dashboard**: 5-10 minutes
- **Detailed Docs**: 30-45 minutes

### 3. Action-Oriented
- Every gap has estimated effort
- Every issue has priority
- Every phase has deliverables
- Every week has clear todos

### 4. Evidence-Based
- Reference file paths
- Reference line numbers
- Link to code examples
- Show actual vs target metrics

### 5. Maintainable
- Keep main file short (< 200 lines)
- Split details into separate files
- Update weekly (not daily)
- Use templates for consistency

---

## 📋 TEMPLATES

### For New Modules

```markdown
# MODULE_NAME MODULE

**Status**: [Basic|Partial|Good|Complete]
**Compliance**: [0-100]%
**Priority**: [P0|P1|P2]

## ✅ Implemented
- Feature 1
- Feature 2

## ❌ Missing
1. Feature 3 (0%)
   - Details...
   - Estimated effort: X days

## 🔧 Priority Actions
1. Task 1 (Day 1-2)
2. Task 2 (Day 3-4)

**Files**:
- path/to/file.ts

**Estimated Effort**: X weeks
```

---

## 🔗 RELATED RESOURCES

**Codebase**:
- [README.md](../../README.md) - Original 1051-line specification
- [OpenAPI Spec](../../packages/openapi/cafe-pos-api.yaml) - API contract (1294 lines)
- [Prisma Schema](../../prisma/schema.prisma) - Database schema

**External**:
- [Hexagonal Architecture Guide](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [SLO Best Practices](https://sre.google/sre-book/service-level-objectives/)

---

**Questions? Issues?**
- Tech Lead: @tech-lead (Slack)
- PM: @project-manager (Slack)
- Docs Repo: GitHub Issues

---

**Last Updated**: 2025-11-06 | **Version**: v1.0.0
