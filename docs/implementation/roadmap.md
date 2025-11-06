# IMPLEMENTATION ROADMAP

**Timeline**: 40-50 weeks (10-12 months)
**Goal**: 20% → 85% compliance with README specification
**Last Updated**: 2025-11-06

---

## 🔴 PHASE 0: FIX CRITICAL BUGS & FOUNDATION (Week 1-2)

**Goal**: Production stability, observability, OpenAPI integration
**Priority**: P0 - MUST DO FIRST
**Team**: 2 backend developers
**Exit Criteria**: Zero critical bugs, full observability, OpenAPI integrated

### Week 1: Fix Bugs & Add Observability

#### Day 1-2: Fix Idempotency Bug ⚠️ CRITICAL
**File**: `apps/api/src/orders/orders.service.ts:36`

**Problem**:
```typescript
async create(createOrderDto: CreateOrderDto, idempotencyKey: string) {
  // ❌ BUG: idempotencyKey received but NOT USED
  // Can create duplicate orders!
}
```

**Solution**:
```typescript
async create(dto: CreateOrderDto, idempotencyKey: string) {
  // 1. Check idempotency first
  const requestHash = this.hashRequest(dto);
  const cached = await this.idempotency.check(idempotencyKey, requestHash);
  if (cached) return cached.response;

  // 2. Create order
  const order = await this.prisma.order.create({...});

  // 3. Store result (24h TTL)
  await this.idempotency.store(idempotencyKey, requestHash, order, 86400);

  return order;
}
```

**Tasks**:
- [ ] Integrate IdempotencyService into OrdersService
- [ ] Add idempotency middleware to all POST endpoints
- [ ] Write integration tests for duplicate requests
- [ ] Verify 409 CONFLICT returned for mismatched bodies

**Deliverable**: Zero duplicate orders possible

---

#### Day 3-5: Add Observability Stack

**Day 3: Structured Logging**
```bash
pnpm add winston winston-daily-rotate-file
```

**Tasks**:
- [ ] Configure Winston with JSON format
- [ ] Add Request ID middleware
- [ ] Add Correlation ID propagation
- [ ] Configure log levels (ERROR, WARN, INFO, DEBUG)
- [ ] Setup daily log rotation (7-day retention)

**Example**:
```typescript
logger.info('Order created', {
  requestId: 'req-123',
  correlationId: 'corr-456',
  userId: 'user-789',
  orderId: 'order-abc',
  total: 150000,
  duration: 45
});
```

**Day 4: Prometheus Metrics**
```bash
pnpm add @willsoto/nestjs-prometheus prom-client
```

**Metrics to Add**:
- `http_request_duration_seconds` (histogram) - API latency
- `http_requests_total` (counter) - Request count by status/method/path
- `active_connections` (gauge) - WebSocket connections
- `db_query_duration_seconds` (histogram) - Database performance
- `redis_operation_duration_seconds` (histogram) - Cache performance
- `payment_success_rate` (gauge) - Payment health
- `order_completion_rate` (gauge) - Business metric

**Day 5: Enhanced Health Check**
- [ ] Database connection pool status
- [ ] Redis connection status
- [ ] Disk space check
- [ ] Memory usage
- [ ] External service health (MoMo API ping)

**Deliverable**: Full observability - can debug production issues with logs + metrics

---

### Week 2: OpenAPI Integration & Resilience

#### Day 1-2: Integrate OpenAPI into Build Pipeline

**OpenAPI spec already exists**: `packages/openapi/cafe-pos-api.yaml` (1294 lines)

**Day 1: Generate TypeScript Types**
```bash
cd packages/openapi
pnpm add -D openapi-typescript
pnpm exec openapi-typescript cafe-pos-api.yaml -o ../shared/src/api-types.ts
```

**Tasks**:
- [ ] Add type generation to build script
- [ ] Export types from `@cafe/shared`
- [ ] Use types in services/controllers
- [ ] Verify type safety (no `any` types)

**Day 2: Generate React Query Client**
```bash
cd packages
mkdir api-client && cd api-client
pnpm add -D @7nohe/openapi-react-query-codegen
pnpm exec openapi-react-query-codegen ../openapi/cafe-pos-api.yaml -o src/
```

**Tasks**:
- [ ] Configure for TanStack Query v5
- [ ] Generate hooks for all endpoints
- [ ] Test in Kiosk app
- [ ] Document usage

**Deliverable**: Frontend auto-generates API client, type-safe

---

#### Day 3-4: Add Schema Validation Middleware

```bash
cd apps/api
pnpm add ajv ajv-formats
```

**Implementation**:
```typescript
// apps/api/src/middleware/schema-validation.middleware.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

export class SchemaValidationMiddleware implements NestMiddleware {
  private ajv: Ajv;

  constructor() {
    this.ajv = new Ajv();
    addFormats(this.ajv);
  }

  use(req: Request, res: Response, next: NextFunction) {
    const schema = this.getSchemaForRoute(req.path, req.method);
    const valid = this.ajv.validate(schema, req.body);

    if (!valid) {
      throw new BadRequestException(this.ajv.errors);
    }

    next();
  }
}
```

**Tasks**:
- [ ] Load schemas from OpenAPI spec
- [ ] Apply to all POST/PATCH/PUT endpoints
- [ ] Return validation errors with clear messages
- [ ] Write tests

**Deliverable**: All requests validated against OpenAPI schema

---

#### Day 5: Add Resilience Patterns

**Circuit Breaker**:
```bash
pnpm add cockatiel
```

```typescript
import { circuitBreaker, ConsecutiveBreaker } from 'cockatiel';

const breaker = circuitBreaker(
  ConsecutiveBreaker({ threshold: 5, halfOpenAfter: 30_000 }),
);

// Wrap external API calls
const result = await breaker.execute(() => this.momoApi.createPayment(data));
```

**Apply to**:
- MoMo payment API
- ZaloPay payment API
- AI services (STT, NLU, TTS)
- Zalo OA messaging
- SMS gateway

**Retry with Exponential Backoff**:
```typescript
import { retry, exponentialBackoff } from 'cockatiel';

const retryPolicy = retry(
  exponentialBackoff({ maxAttempts: 3, initialDelay: 100, maxDelay: 5000 }),
);

const result = await retryPolicy.execute(() => this.externalService.call());
```

**Timeouts**:
- API requests: 10s
- Database queries: 5s
- Redis operations: 1s
- External services: 15s

**Tasks**:
- [ ] Add circuit breaker to all external calls
- [ ] Add retry logic with jitter
- [ ] Configure timeouts
- [ ] Test failure scenarios
- [ ] Add metrics (circuit breaker state)

**Deliverable**: System handles external failures gracefully

---

### Phase 0 Success Metrics

- ✅ Zero idempotency bugs in production
- ✅ Full observability (logs in JSON format, metrics in Prometheus)
- ✅ OpenAPI types auto-generated and used
- ✅ Circuit breaker on all external calls
- ✅ Test coverage > 0% (critical paths covered)
- ✅ Production stability improved (zero data integrity issues)

---

## 🟡 PHASE 1: COMPLETE CORE POS FEATURES (Week 3-10)

**Goal**: 60% → 90% compliance for core POS features
**Priority**: P1 - HIGH
**Team**: 2 backend developers
**Duration**: 8 weeks

### Week 3-4: Complete Promotions Module (60% → 90%)

**Current State**: Basic features work (PERCENTAGE, FIXED_AMOUNT)
**Gap**: Missing advanced types (BUY_X_GET_Y, COMBO_PRICE, time-based)

#### Week 3: Advanced Promotion Types

**Tasks**:
1. **Implement BUY_X_GET_Y Logic** (2 days)
   - Parse rules: "buy 2 coffee, get 1 free"
   - Match items in order by SKU/category
   - Calculate discount (free item price or %)
   - Handle "cheapest free" vs "most expensive free"

2. **Implement COMBO_PRICE Logic** (2 days)
   - Define combo bundles (e.g., "1 coffee + 1 cake = 50k")
   - Match bundle items in order
   - Apply bundle pricing
   - Handle partial matches

3. **Add Time-Based Promotions** (1 day)
   - Golden hour support (e.g., "2-4pm happy hour")
   - Day-of-week restrictions
   - Schedule validation in `applyPromotion()`

**Files**:
- `promotions/promotions.service.ts` - Update `applyPromotion()`
- `promotions/promotion-rules.util.ts` - New utility for complex rules

**Deliverable**: All promotion types working

---

#### Week 4: Promotion Analytics

**Tasks**:
1. **Promotion Simulator** (2 days)
   - Endpoint: `POST /promotions/simulate`
   - Test promotion against past orders (last 30 days)
   - Return: potential discount, uplift %, orders affected
   - Use case: Validate promotion before launch

2. **Hold-out Groups (A/B Testing)** (2 days)
   - Define control group (no promotion)
   - Define treatment group (with promotion)
   - Random assignment (50/50 split)
   - Calculate statistical significance
   - Database: `promotion_experiments` table

3. **Priority System** (1 day)
   - When multiple promotions apply, pick best for customer
   - Configurable priority rules
   - Anti double-dip enforcement

**Files**:
- `promotions/promotion-simulator.service.ts` - New service
- `promotions/ab-testing.service.ts` - New service
- `promotions/promotion-priority.util.ts` - Priority logic

**Deliverable**: Promotion simulator + A/B testing framework

---

### Week 5-6: Complete Reports Module (50% → 80%)

**Current State**: 6 basic reports (daily sales, top selling, etc.)
**Gap**: Missing advanced analytics (CM, uplift, labor)

#### Week 5: Contribution Margin & Uplift

**Tasks**:
1. **Contribution Margin Reports** (2 days)
   - Calculate COGS per item from BOM
   - Formula: Revenue - COGS = CM
   - CM % by item/category
   - Endpoint: `GET /reports/contribution-margin`

2. **Promo Uplift Analysis** (2 days)
   - Compare orders with vs without promotion
   - Metrics:
     - Uplift % = (Treatment - Control) / Control * 100
     - Incremental revenue
     - ROI per promotion
   - Endpoint: `GET /reports/promotion-uplift`

3. **Device Health Reports** (1 day)
   - Printer uptime %
   - KDS response time
   - Device heartbeat status
   - Endpoint: `GET /reports/devices`

**Deliverable**: Advanced analytics reports

---

#### Week 6: Labor Reports

**Tasks**:
1. **Labor Cost Reports** (2 days)
   - Hours worked (from attendance table)
   - Labor cost = hours × hourly_rate
   - Revenue per labor hour
   - Productivity metrics
   - Endpoint: `GET /reports/labor`

2. **Payment Success Rate** (1 day)
   - Success rate by gateway (MoMo, ZaloPay)
   - Average processing time
   - Failed payment reasons
   - Endpoint: `GET /reports/payments`

3. **Reconciliation Status** (2 days)
   - D+1 matching (expected vs actual)
   - Discrepancies table
   - Alert for mismatches
   - Endpoint: `GET /reports/reconciliation`

**Deliverable**: Labor + Payment analytics

---

### Week 7-10: Complete Inventory Module (40% → 80%)

**Current State**: Basic CRUD for inventory items
**Gap**: Missing BOM, PO/GRN, OCR

#### Week 7-8: BOM & Recipe Management

**Tasks**:
1. **BOM/Recipe System** (3 days)
   - Database: `bom_recipes`, `bom_items` tables
   - Define recipe per menu item
   - Ingredient quantities (e.g., "1 Latte = 30ml espresso + 200ml milk")
   - Size-based recipes (S/M/L variants)
   - Endpoint: `POST /bom/recipes`

2. **Recipe Costing** (2 days)
   - Calculate COGS from BOM + ingredient costs
   - Auto-update when ingredient price changes
   - Store in `menu_items.cogs` field
   - Used by CM reports

**Deliverable**: Full BOM system for costing

---

#### Week 9: PO/GRN Workflow

**Tasks**:
1. **Purchase Order Creation** (2 days)
   - Endpoint: `POST /inventory/purchase-orders`
   - Fields: supplier, items, quantities, expected_date
   - Status: DRAFT → SENT → RECEIVED
   - Generate PO number

2. **Goods Received Note** (2 days)
   - Endpoint: `POST /inventory/grn`
   - Link to PO
   - Record actual quantities received
   - Create stock IN movements
   - Update inventory levels

3. **PO-GRN Linking** (1 day)
   - Track PO → GRN → Stock
   - Variance report (ordered vs received)
   - Alert for discrepancies

**Deliverable**: Full PO/GRN workflow

---

#### Week 10: OCR Invoice Scanning

**Tasks**:
1. **OCR Integration** (2 days)
   - Option 1: Tesseract.js (local, free)
   - Option 2: Google Vision API (cloud, paid)
   - Endpoint: `POST /inventory/ocr/scan`
   - Input: Invoice image (base64)
   - Output: Parsed supplier, date, items, quantities, prices

2. **Auto-Create Stock Movements** (2 days)
   - Parse OCR result → Create GRN
   - Validate against expected PO
   - Flag mismatches for manual review
   - Update inventory levels

3. **Testing & Accuracy** (1 day)
   - Test with Vietnamese invoices
   - Tune OCR parameters
   - Handle errors gracefully

**Deliverable**: OCR for supplier invoices

---

### Phase 1 Success Metrics

- ✅ Promotions: 90% (all types working, simulator + A/B testing)
- ✅ Reports: 80% (CM, uplift, labor, payments, reconciliation)
- ✅ Inventory: 80% (BOM, PO/GRN, OCR)
- ✅ Core POS production-ready for scale

---

## 🟢 PHASE 2A: FACEID RECOGNITION (Week 11-15) ⭐ HIGHEST PRIORITY

**Goal**: 0% → 85% FaceID system
**Priority**: P1 - HIGHEST BUSINESS IMPACT
**Team**: 1 ML engineer + 1 backend developer
**Duration**: 5 weeks

**Why This Matters**: FaceID is THE core differentiator. Without it, this is just a normal POS.

### Week 11: Infrastructure Setup

**Tasks**:
1. **Setup pgvector Extension** (1 day)
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;

   CREATE TABLE face_embeddings (
     customer_id uuid PRIMARY KEY REFERENCES customers(id),
     embedding vector(128) NOT NULL,
     enc_method text DEFAULT 'aes-256-gcm',
     created_at timestamptz DEFAULT now(),
     updated_at timestamptz DEFAULT now()
   );

   CREATE INDEX idx_face_embeddings_vec
     ON face_embeddings USING ivfflat (embedding vector_cosine_ops)
     WITH (lists = 100);
   ```

2. **Download Models** (2 days)
   - YuNet face detector (ONNX) - 5-point landmark
   - MobileFaceNet embedder (int8) - Lite profile
   - ArcFace R50 embedder (int8) - Balanced profile
   - Anti-spoof model (liveness detection)

3. **Setup ONNX Runtime** (2 days)
   ```bash
   pnpm add onnxruntime-node
   ```
   - Load models on app startup
   - Warm up with dummy input
   - Benchmark inference time

**Deliverable**: Models loaded, inference < 100ms per step

---

### Week 12-13: Core Recognition Pipeline

**Week 12: Detection + Embedding**

**Tasks**:
1. **Face Detection** (2 days)
   - YuNet detector: image → bounding box + 5 landmarks
   - Target: < 100ms p95
   - Handle multiple faces (return all)

2. **Face Alignment** (1 day)
   - 5-point alignment (eyes, nose, mouth corners)
   - Crop to 112x112 (standard face recognition size)
   - Normalize pixel values

3. **Embedding Extraction** (2 days)
   - MobileFaceNet or ArcFace: image → 128-dim vector
   - Target: < 100ms p95
   - Normalize embedding (L2 norm)

**Week 13: Vector Search + Matching**

**Tasks**:
1. **Vector Similarity Search** (2 days)
   ```typescript
   // Find nearest neighbors
   const query = `
     SELECT customer_id,
            embedding <=> $1::vector AS distance,
            1 - (embedding <=> $1::vector) AS similarity
     FROM face_embeddings
     WHERE (embedding <=> $1::vector) < 0.25  -- threshold
     ORDER BY distance
     LIMIT 1;
   `;
   ```
   - Cosine similarity (0-1 scale)
   - Threshold: 0.75 (Lite), 0.78 (Balanced), 0.80 (Max)
   - Target: < 100ms p95

2. **Match Logic** (1 day)
   - If similarity > threshold → MATCH (return customer_id)
   - Else → NO MATCH (prompt opt-in)
   - Log confidence score

3. **Performance Optimization** (2 days)
   - IVFFlat index tuning (lists parameter)
   - Consider HNSW for scale (> 10k faces)
   - Benchmark with 1k, 10k, 100k faces

**Deliverable**: End-to-end pipeline: image → customer_id in < 300ms

---

### Week 14: Liveness Detection & Security

**Tasks**:
1. **Anti-Spoof Model** (2 days)
   - Detect printed photos, screen replays
   - Model: MobileNet-based classifier
   - Output: real/fake probability
   - Only for Balanced/Max profiles

2. **Encryption** (1 day)
   ```typescript
   import crypto from 'crypto';

   function encryptEmbedding(embedding: number[]): Buffer {
     const key = process.env.FACE_ENCRYPTION_KEY; // 32 bytes
     const iv = crypto.randomBytes(16);
     const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

     const encrypted = Buffer.concat([
       cipher.update(Buffer.from(new Float32Array(embedding).buffer)),
       cipher.final(),
     ]);

     const authTag = cipher.getAuthTag();
     return Buffer.concat([iv, authTag, encrypted]);
   }
   ```

3. **GDPR Compliance** (2 days)
   - Opt-in consent flow
   - Consent storage (`customer_consents` table)
   - DELETE endpoint for right to be forgotten
   - Audit log for all face accesses

**Deliverable**: Secure, GDPR-compliant FaceID system

---

### Week 15: API Endpoints & Integration

**Tasks**:
1. **POST /face/recognize** (2 days)
   ```typescript
   interface RecognizeRequest {
     image: string; // base64
     profile?: 'lite' | 'balanced' | 'max';
   }

   interface RecognizeResponse {
     matched: boolean;
     customerId?: string;
     confidence?: number;
     loyaltyPoints?: number;
     recommendations?: MenuItem[];
     greeting?: string; // for TTS
   }
   ```

2. **POST /customers/:id/face/register** (1 day)
   - Check opt-in consent first
   - Extract embedding
   - Encrypt and store
   - Return success

3. **DELETE /customers/:id/face/delete** (1 day)
   - GDPR right to delete
   - Remove embedding
   - Remove consent
   - Audit log

4. **Integration with Loyalty + Recommendations** (1 day)
   - On MATCH: Fetch loyalty account
   - Fetch purchase history
   - Get personalized recommendations
   - Generate TTS greeting

**Deliverable**: FaceID API ready for Kiosk integration

---

### Phase 2A Success Metrics

- ✅ Face detection: < 100ms p95
- ✅ Embedding extraction: < 100ms p95
- ✅ Vector search: < 100ms p95
- ✅ Total latency: < 300ms p95
- ✅ False Accept Rate: < 0.01%
- ✅ False Reject Rate: < 1%
- ✅ Opt-in rate: > 60% (track over time)
- ✅ GDPR compliant (consent + delete working)

---

## 🔵 PHASE 2B: VOICE AI SYSTEM (Week 16-23)

**Goal**: 0% → 80% Voice AI (STT, NLU, TTS, PromptOps)
**Priority**: P1 - CRITICAL FOR VOICE-FIRST KIOSK
**Team**: 2 backend developers + 1 frontend developer
**Duration**: 8 weeks

[Detailed week-by-week plan for Voice AI system...]

---

## 🟣 PHASE 2C-E: REMAINING AI FEATURES (Week 24-37)

**Phase 2C**: Demand Forecasting (4 weeks)
**Phase 2D**: Recommend Engine + Anomaly (5 weeks)
**Phase 2E**: Workforce Management (4 weeks)

[Detailed plans...]

---

## 🟠 PHASE 3: FRONTEND COMPLETION (Week 38-45)

**Kiosk App**: Voice-first UI (4 weeks)
**Admin Dashboard**: 10 modules (4 weeks)

[Detailed plans...]

---

## 🟤 PHASE 4: CRM & MESSAGING (Week 46-51)

**Zalo OA + SMS + Email**: 6 weeks

[Detailed plans...]

---

## 🟢 PHASE 5: PRODUCTION POLISH (Week 52-53)

**Testing, Optimization, Documentation**: 2 weeks

[Detailed plans...]

---

**Last Updated**: 2025-11-06
**Next Review**: After each phase completion
