# TECHNICAL DEBT & GAPS

**Last Updated**: 2025-11-06
**Overall Tech Debt**: High (Multiple critical issues)

---

## 🚨 CRITICAL ISSUES (Must Fix in Phase 0)

### 1. Idempotency Bug ⚠️ DATA INTEGRITY RISK

**File**: `apps/api/src/orders/orders.service.ts:36`

**Problem**:
```typescript
async create(createOrderDto: CreateOrderDto, idempotencyKey: string) {
  // ❌ BUG: idempotencyKey parameter exists but NOT USED
  // Can create duplicate orders if request retried!
}
```

**Impact**:
- Customer charged twice
- Duplicate orders in database
- Inventory double-deducted
- Loyalty points double-earned

**Fix** (3 hours):
```typescript
async create(dto: CreateOrderDto, idempotencyKey: string) {
  // 1. Check idempotency
  const hash = this.hashRequest(dto);
  const cached = await this.idempotency.check(idempotencyKey, hash);
  if (cached) return cached.response;

  // 2. Create order (existing logic)
  const order = await this.prisma.order.create({...});

  // 3. Store result (24h TTL)
  await this.idempotency.store(idempotencyKey, hash, order, 86400);

  return order;
}
```

**Priority**: 🔴 P0 - Fix this week!

---

### 2. Zero Observability ⚠️ BLIND IN PRODUCTION

**Current State**:
```typescript
// Only basic console.log
console.log('Order created:', order.id);
this.logger.log('Payment succeeded');
```

**Problems**:
- Cannot debug production issues
- No request tracing (no correlation IDs)
- No performance metrics
- No alerting
- Cannot measure SLOs

**Required**:

#### 2.1 Structured Logging (Winston/Pino)
```typescript
import { Logger } from '@nestjs/common';

logger.info('Order created', {
  requestId: 'req-abc-123',
  correlationId: 'corr-xyz-456',
  userId: 'user-789',
  orderId: 'order-def',
  total: 150000,
  duration: 45,
  timestamp: new Date().toISOString(),
});
```

**Output** (JSON):
```json
{
  "level": "info",
  "message": "Order created",
  "requestId": "req-abc-123",
  "correlationId": "corr-xyz-456",
  "userId": "user-789",
  "orderId": "order-def",
  "total": 150000,
  "duration": 45,
  "timestamp": "2025-11-06T10:30:45.123Z"
}
```

#### 2.2 Prometheus Metrics
```typescript
import { Counter, Histogram, Gauge } from 'prom-client';

// Request metrics
const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration',
  labelNames: ['method', 'route', 'status'],
});

const httpRequestsTotal = new Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'route', 'status'],
});

// Business metrics
const ordersTotal = new Counter({
  name: 'orders_total',
  help: 'Total orders created',
  labelNames: ['branch', 'status'],
});

const paymentSuccessRate = new Gauge({
  name: 'payment_success_rate',
  help: 'Payment success rate (last 5 min)',
});
```

#### 2.3 OpenTelemetry Traces
```typescript
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('cafe-pos-api');

const span = tracer.startSpan('create_order');
span.setAttribute('order.id', order.id);
span.setAttribute('order.total', order.total);

try {
  // Create order...
  span.setStatus({ code: SpanStatusCode.OK });
} catch (error) {
  span.recordException(error);
  span.setStatus({ code: SpanStatusCode.ERROR });
} finally {
  span.end();
}
```

**Priority**: 🔴 P0 - Fix this week!
**Effort**: 2 days

---

### 3. Zero Tests ⚠️ CANNOT REFACTOR SAFELY

**Current State**:
```bash
$ find apps/api -name "*.spec.ts" | wc -l
0
```

**Test Coverage**: **0%**

**Problems**:
- Cannot refactor without breaking things
- No regression protection
- No contract validation
- Manual testing only (slow, error-prone)

**Required Test Coverage**:

| Layer | Coverage Target | Priority |
|-------|----------------|----------|
| **Critical Paths** | 100% | 🔴 P0 |
| Unit Tests | 80% | 🟡 P1 |
| Integration Tests | 60% | 🟡 P1 |
| E2E Tests | 30% | 🟢 P2 |

**Critical Paths to Test First**:
1. Orders: Create, update status, apply promotion
2. Payments: IPN webhook, HMAC verification, deduplication
3. Idempotency: Duplicate request handling
4. Authentication: JWT validation, RLS
5. Loyalty: Earn, redeem, balance check

**Testing Stack**:
```bash
pnpm add -D vitest @vitest/coverage-v8
pnpm add -D @nestjs/testing
pnpm add -D supertest
```

**Example Unit Test**:
```typescript
import { Test } from '@nestjs/testing';
import { OrdersService } from './orders.service';

describe('OrdersService', () => {
  let service: OrdersService;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [OrdersService],
    }).compile();

    service = module.get<OrdersService>(OrdersService);
  });

  it('should create order with idempotency', async () => {
    const dto = { items: [...], total: 100000 };
    const key = 'uuid-123';

    // First call
    const order1 = await service.create(dto, key);
    expect(order1.id).toBeDefined();

    // Second call with same key → should return cached
    const order2 = await service.create(dto, key);
    expect(order2.id).toBe(order1.id);
  });
});
```

**Priority**: 🔴 P0 - Start this week!
**Effort**: 1 week for critical paths, ongoing for full coverage

---

## 🟡 ARCHITECTURE VIOLATIONS (Phase 2 Refactor)

### Current Architecture: Layered (Violations)

```
Controller → Service → Prisma
           ↓
    (Mixed concerns)
```

**Problems**:
- Business logic + infrastructure mixed
- Hard to test (tight coupling to Prisma)
- Hard to swap implementations (e.g., switch to MongoDB)
- Violates README Hexagonal Architecture requirement

**Example Violation**:
```typescript
// orders/orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    private prisma: PrismaService,  // ❌ Direct dependency on infrastructure
    private promotions: PromotionsService,
    private kds: KdsService,
    private loyalty: LoyaltyService,
  ) {}

  async create(dto: CreateOrderDto) {
    // ❌ Business logic + infrastructure mixed
    const order = await this.prisma.order.create({...});

    // ❌ Business logic scattered
    if (dto.promotionCode) {
      const discount = await this.promotions.applyPromotion(...);
      order.discount = discount;
    }

    // ❌ Side effects in service
    await this.kds.createTicketsForOrder(order);
    await this.loyalty.earnPoints(order.customerId, points);

    return order;
  }
}
```

---

### Required Architecture: Hexagonal (Clean)

```
┌─────────────────────────────────────────────────┐
│                   API Layer                     │
│  (Controllers, DTOs, Middleware)                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              Application Layer                  │
│  (Use Cases, Ports, Application Services)       │
│                                                 │
│  CreateOrderUseCase                             │
│  ├─> orderRepository.save(order)                │
│  ├─> promotionEngine.apply(order)               │
│  ├─> kdsGateway.createTicket(order)             │
│  └─> loyaltyService.earnPoints(customer)        │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│                Domain Layer                     │
│  (Entities, Value Objects, Domain Services)     │
│                                                 │
│  Order Entity                                   │
│  ├─> calculateTotal()                           │
│  ├─> applyDiscount(discount)                    │
│  ├─> validateItems()                            │
│  └─> emit OrderCreatedEvent                     │
│                                                 │
│  Money Value Object                             │
│  Customer Entity                                │
└─────────────────────────────────────────────────┘
                 ▲
┌────────────────┴────────────────────────────────┐
│            Infrastructure Layer                 │
│  (Adapters: Prisma, Redis, MoMo, etc.)         │
│                                                 │
│  OrderRepositoryAdapter (implements Port)       │
│  MoMoPaymentGatewayAdapter (implements Port)    │
│  RedisIdempotencyAdapter (implements Port)      │
└─────────────────────────────────────────────────┘
```

**Refactored Example**:
```typescript
// domain/order/entities/order.entity.ts
export class Order {
  constructor(
    public readonly id: string,
    public items: OrderItem[],
    public discount: Money,
    public status: OrderStatus,
  ) {}

  calculateTotal(): Money {
    const subtotal = this.items.reduce((sum, item) =>
      sum.add(item.subtotal), Money.zero()
    );
    return subtotal.subtract(this.discount);
  }

  applyDiscount(discount: Money): void {
    if (discount.isNegative()) {
      throw new DomainException('Discount cannot be negative');
    }
    this.discount = discount;
  }

  // Pure business logic, no infrastructure!
}

// application/use-cases/create-order.use-case.ts
export class CreateOrderUseCase {
  constructor(
    private orderRepository: OrderRepositoryPort,  // ✅ Port (interface)
    private promotionEngine: PromotionEnginePort,
    private kdsGateway: KdsGatewayPort,
    private loyaltyService: LoyaltyServicePort,
    private eventBus: EventBusPort,
  ) {}

  async execute(command: CreateOrderCommand): Promise<Order> {
    // 1. Create domain entity
    const order = Order.create(command);

    // 2. Apply promotion (domain service)
    if (command.promotionCode) {
      const discount = await this.promotionEngine.calculate(order);
      order.applyDiscount(discount);
    }

    // 3. Validate
    order.validate();

    // 4. Persist (through port)
    await this.orderRepository.save(order);

    // 5. Side effects (async, non-blocking)
    await this.eventBus.publish(new OrderCreatedEvent(order));

    return order;
  }
}

// infrastructure/adapters/order-repository.adapter.ts
export class OrderRepositoryAdapter implements OrderRepositoryPort {
  constructor(private prisma: PrismaService) {}

  async save(order: Order): Promise<void> {
    await this.prisma.order.create({
      data: {
        id: order.id,
        items: order.items.map(item => ({...})),
        total: order.calculateTotal().amount,
      },
    });
  }

  async findById(id: string): Promise<Order | null> {
    const data = await this.prisma.order.findUnique({ where: { id } });
    if (!data) return null;

    // Map Prisma model → Domain entity
    return Order.reconstruct(data);
  }
}
```

**Benefits**:
- ✅ Business logic isolated (testable without DB)
- ✅ Infrastructure swappable (switch Prisma → TypeORM)
- ✅ Clear separation of concerns
- ✅ Domain-Driven Design (DDD) compliant

**Priority**: 🟡 P2 - Refactor after Phase 0
**Effort**: 3 weeks (gradual migration)

---

## 🟢 MISSING DEVELOPER PROCESS (Phase 0)

### 1. CI/CD Pipeline (0%) ⚠️ NO AUTOMATION

**Current State**:
```bash
$ ls .github/workflows/
ls: .github/workflows/: No such file or directory
```

**Problems**:
- Manual deployment (error-prone)
- No automated tests on PR
- No smoke tests after deploy
- No rollback strategy

**Required**:
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      - name: Install dependencies
        run: pnpm install
      - name: Lint
        run: pnpm lint
      - name: Test
        run: pnpm test
      - name: Build
        run: pnpm build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: ./scripts/deploy-staging.sh
      - name: Smoke tests
        run: pnpm test:e2e:staging
      - name: Deploy to production
        run: ./scripts/deploy-production.sh
```

**Priority**: 🔴 P0 - Setup this week
**Effort**: 2 days

---

### 2. Code Quality Tools (20%)

**Current**:
- ✅ ESLint configured
- ✅ Prettier configured
- ❌ No pre-commit hooks
- ❌ No conventional commits
- ❌ No changelog generation

**Required**:
```bash
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional
```

```json
// package.json
{
  "scripts": {
    "prepare": "husky install"
  },
  "lint-staged": {
    "*.ts": ["eslint --fix", "prettier --write"],
    "*.md": ["prettier --write"]
  }
}
```

```yaml
# .husky/pre-commit
#!/bin/sh
pnpm lint-staged
pnpm test:changed
```

**Priority**: 🟡 P1 - Setup Week 2
**Effort**: 1 day

---

### 3. Contract Tests (0%)

**Missing**:
- MoMo adapter contract tests
- ZaloPay adapter contract tests
- Zalo OA adapter contract tests
- OpenAPI schema validation tests

**Example Contract Test**:
```typescript
import { MoMoAdapter } from './momo.adapter';

describe('MoMo Adapter Contract', () => {
  it('should match MoMo API contract', async () => {
    const adapter = new MoMoAdapter();

    const response = await adapter.createPayment({
      amount: 100000,
      orderId: 'test-123',
    });

    // Validate response matches MoMo contract
    expect(response).toHaveProperty('payUrl');
    expect(response).toHaveProperty('deeplink');
    expect(response.payUrl).toMatch(/^https:\/\/test-payment.momo.vn/);
  });

  it('should verify HMAC correctly', () => {
    const ipnData = {...};
    const signature = MoMoHmacUtil.generateSignature(ipnData);

    expect(MoMoHmacUtil.verifySignature(ipnData, signature)).toBe(true);
  });
});
```

**Priority**: 🟡 P1 - Week 2
**Effort**: 2 days

---

## 📊 TECHNICAL DEBT SUMMARY

| Issue | Impact | Priority | Effort | Phase |
|-------|--------|----------|--------|-------|
| **Idempotency Bug** | Critical | 🔴 P0 | 3h | Phase 0 Week 1 |
| **Zero Observability** | Critical | 🔴 P0 | 2d | Phase 0 Week 1 |
| **Zero Tests** | Critical | 🔴 P0 | 1w | Phase 0 Week 1 |
| **No CI/CD** | High | 🔴 P0 | 2d | Phase 0 Week 2 |
| **OpenAPI Not Used** | High | 🔴 P0 | 2d | Phase 0 Week 2 |
| **No Resilience** | High | 🔴 P0 | 1d | Phase 0 Week 2 |
| **Code Quality** | Medium | 🟡 P1 | 1d | Phase 0 Week 2 |
| **Contract Tests** | Medium | 🟡 P1 | 2d | Phase 0 Week 2 |
| **Architecture** | Medium | 🟡 P2 | 3w | Phase 2 |

**Total Phase 0 Effort**: 2 weeks (10 working days)

---

## 🎯 PRIORITY ORDER

### Week 1 (Phase 0):
1. **Day 1-2**: Fix idempotency bug ⚠️
2. **Day 3**: Add structured logging (Winston)
3. **Day 4**: Add Prometheus metrics
4. **Day 5**: Write critical path tests

**Exit Criteria**:
- ✅ Zero idempotency bugs
- ✅ JSON logs with request IDs
- ✅ Prometheus /metrics endpoint
- ✅ Test coverage > 0% (critical paths)

### Week 2 (Phase 0):
1. **Day 1-2**: Integrate OpenAPI (types + validation)
2. **Day 3**: Add resilience patterns (circuit breaker, retry)
3. **Day 4**: Setup CI/CD pipeline
4. **Day 5**: Code quality tools (husky, lint-staged)

**Exit Criteria**:
- ✅ OpenAPI types auto-generated
- ✅ Circuit breaker on external calls
- ✅ CI/CD running on PRs
- ✅ Pre-commit hooks working

---

**Last Updated**: 2025-11-06
**Next Review**: After Phase 0 completion (Nov 20)
