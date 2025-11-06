# 📋 QUICK REFERENCE CARD

**Print this page and pin it on your wall!**
**Last Updated**: 2025-11-06

---

## 🎯 CURRENT SPRINT

```
┌─────────────────────────────────────────────────────┐
│ PHASE 0 - WEEK 1: FIX CRITICAL BUGS                │
│ Sprint: 2025-11-06 to 2025-11-13                   │
│ Team: 2 Backend Developers                          │
│ Focus: Idempotency + Observability                  │
└─────────────────────────────────────────────────────┘
```

---

## ✅ THIS WEEK TODO (Week of Nov 6)

| Day | Task | File | Owner | Status |
|-----|------|------|-------|--------|
| Mon-Tue | Fix idempotency bug | `orders/orders.service.ts:36` | Backend | ⏳ |
| Wed | Add Winston logging | `common/logging/` | Backend | ⏳ |
| Thu | Add Prometheus metrics | `common/metrics/` | Backend | ⏳ |
| Fri | Write critical tests | `**/*.spec.ts` | Backend | ⏳ |

**Exit Criteria**: Zero idempotency bugs, logs in JSON, metrics in Prometheus

---

## 🚨 CRITICAL NUMBERS

```
Overall Compliance:      20% ████░░░░░░░░░░░░░░░░ (Target: 85%)
Current Phase:           Phase 0 (Week 1 of 2)
Timeline to 85%:         40-50 weeks
Test Coverage:           0% (Target: 80%)
Production Incidents:    0 this week (Keep it!)
```

---

## 🔴 CRITICAL BLOCKERS

1. **Idempotency Bug** - `orders.service.ts:36` → Fix by Tuesday
2. **Zero Observability** - Blind in production → Add Winston + Prometheus by Thursday
3. **No Tests** - Cannot refactor safely → Start writing tests Friday

---

## 📊 MODULE COMPLIANCE AT A GLANCE

| Module | Status | % | Next Action |
|--------|--------|---|-------------|
| Backend Core | ✅ | 100% | Maintain |
| Auth & Security | ✅ | 70% | Phase 0 |
| Promotions | 🟡 | 60% | Phase 1 (Week 3-4) |
| Reports | 🟡 | 50% | Phase 1 (Week 5-6) |
| Inventory | 🟡 | 40% | Phase 1 (Week 7-10) |
| **FaceID** | 🔴 | 0% | Phase 2A (Week 11-15) ⭐ |
| **Voice AI** | 🔴 | 0% | Phase 2B (Week 16-23) |
| Frontend | 🔴 | 15% | Phase 3 (Week 38-45) |
| CRM | 🔴 | 0% | Phase 4 (Week 46-51) |

---

## 🛤️ CRITICAL PATH (Simplified)

```
Phase 0 (2w) ──┬──> Phase 1 (8w) ──┐
               │                     │
               ├──> Phase 2A (5w) ──┤
               │    FaceID ⭐        ├──> Phase 5 (2w)
               │                     │    Production
               ├──> Phase 2B (8w) ──┤
               │    Voice AI         │
               │                     │
               └──> Phase 3-4 (14w)─┘
                    Frontend + CRM
```

**Bottleneck**: Phase 0 blocks EVERYTHING → Must finish by Nov 20!

---

## ⚠️ TOP 3 RISKS THIS WEEK

1. **Idempotency fix breaks existing orders** → Test thoroughly!
2. **Observability adds latency** → Benchmark before/after
3. **Team blocked by missing docs** → Update docs as you go

---

## 📞 EMERGENCY CONTACTS

**Tech Lead**: @tech-lead (Slack)
**README Source**: `README.md` (1051 lines)
**OpenAPI Spec**: `packages/openapi/cafe-pos-api.yaml` (1294 lines)
**Master Status**: `MASTER-STATUS.md`

---

## 📚 QUICK LINKS

| What | Where |
|------|-------|
| **Full Roadmap** | [docs/implementation/roadmap.md](implementation/roadmap.md) |
| **AI System Details** | [docs/implementation/ai-system.md](implementation/ai-system.md) |
| **Backend Modules** | [docs/implementation/backend-modules.md](implementation/backend-modules.md) |
| **Technical Debt** | [docs/implementation/technical-debt.md](implementation/technical-debt.md) |

---

## 🎯 KEY METRICS TO TRACK

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Idempotency Bug | 🔴 Exists | ✅ Fixed | Nov 12 |
| JSON Logging | ❌ No | ✅ Yes | Nov 13 |
| Prometheus Metrics | ❌ No | ✅ Yes | Nov 13 |
| Test Coverage | 0% | 20% | Nov 13 |
| Compliance % | 20% | 22% | Nov 13 |

---

## 💡 REMEMBER

✅ **DO**:
- Check MASTER-STATUS.md before starting new work
- Update todos when status changes
- Write tests for critical paths
- Ask when uncertain

❌ **DON'T**:
- Push to main without tests
- Skip idempotency checks
- Add features without compliance check
- Work in silos (communicate!)

---

## 🔄 WEEKLY REVIEW

**Next Review**: Monday, Nov 13, 10:00 AM
**Agenda**:
- Review Phase 0 Week 1 completion
- Demo idempotency fix
- Show observability dashboard
- Plan Phase 0 Week 2 (OpenAPI + Resilience)

---

**🚀 Let's ship production-grade code!**

**Last Updated**: 2025-11-06 | **Version**: v5.3.1
