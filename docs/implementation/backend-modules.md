# BACKEND MODULES STATUS

**Last Updated**: 2025-11-06
**Overall Backend Compliance**: 60-100% (varies by module)

---

## 📊 MODULES OVERVIEW

| Module | Status | Compliance | Files | Priority | Notes |
|--------|--------|------------|-------|----------|-------|
| **Backend Core** | ✅ Complete | 100% | 17 modules | - | Production ready |
| **Authentication** | ✅ Complete | 100% | 8 files | - | JWT + RBAC + RLS working |
| **Orders** | 🟢 Good | 80% | 4 files | P1 | Missing split bill, refund |
| **Payments** | 🟢 Good | 90% | 5 files | P0 | Missing reconciliation |
| **Promotions** | 🟡 Partial | 60% | 4 files | P1 | Missing BUY_X_GET_Y, simulator |
| **Reports/KPIs** | 🟡 Partial | 50% | 2 files | P1 | Missing CM, labor reports |
| **Loyalty** | 🟡 Partial | 40% | 3 files | P2 | Missing gift card, expiry |
| **Inventory** | 🔴 Basic | 40% | 3 files | P1 | Missing BOM, PO/GRN, OCR |
| **Menu** | 🔴 Basic | 40% | 2 files | P2 | Missing modifiers, combos |
| **KDS** | 🟡 Partial | 60% | 3 files | P2 | Missing ETA, balancing |
| **Printer** | 🟢 Good | 80% | 2 files | P2 | Missing stall detection |
| **Receipts** | 🟢 Good | 90% | 1 file | - | Production ready |
| **Customers** | 🟡 Partial | 50% | 2 files | P2 | Missing verification, consent |
| **WebSocket** | 🟡 Partial | 30% | 2 files | P2 | Missing real-time updates |
| **Health** | ✅ Complete | 100% | 1 file | - | Production ready |

---

## ✅ 1. BACKEND CORE (100% Complete)

**Status**: Production ready, no action needed

**Modules** (17 total):
- NestJS application
- Prisma ORM
- PostgreSQL database
- Redis cache
- Bull queue
- Environment config
- Error handling
- Logging (basic)
- API versioning
- CORS setup
- Request validation
- Rate limiting
- Health checks
- Docker support
- Monorepo structure (Turborepo)
- TypeScript strict mode
- ESLint + Prettier

**Files**:
- `apps/api/src/main.ts` - Application bootstrap
- `apps/api/src/app.module.ts` - Root module
- `prisma/schema.prisma` - Database schema (complete)

**No Gaps**: All core infrastructure working

---

## ✅ 2. AUTHENTICATION & AUTHORIZATION (100% Complete)

**Status**: Production ready, deployed in v5.3.1

**Features**:
- ✅ JWT authentication (1h expiration)
- ✅ Login/Register endpoints
- ✅ Password hashing (bcrypt, 10 rounds)
- ✅ Role-Based Access Control (ADMIN, MANAGER, CASHIER, VIEWER)
- ✅ Row-Level Security (BranchAccessService)
- ✅ @Public() decorator
- ✅ @Roles() decorator
- ✅ @CurrentUser() decorator
- ✅ JwtAuthGuard (global)
- ✅ RolesGuard

**Files**:
- `auth/auth.module.ts`
- `auth/auth.service.ts`
- `auth/auth.controller.ts`
- `auth/strategies/jwt.strategy.ts`
- `auth/strategies/local.strategy.ts`
- `auth/guards/jwt-auth.guard.ts`
- `auth/guards/roles.guard.ts`
- `auth/services/branch-access.service.ts`

**Example Usage**:
```typescript
@Post()
@Roles('ADMIN', 'MANAGER')
async create(@CurrentUser() user: User, @Body() dto: CreateOrderDto) {
  // Only ADMIN or MANAGER can create
  // user.branchId used for RLS
}
```

**No Gaps**: Full compliance with README auth requirements

---

## 🟢 3. ORDERS MODULE (80% Complete)

**Status**: Good, missing advanced POS features

### ✅ Implemented

**Core Features**:
- ✅ Create order (POST /orders)
- ✅ List orders with pagination (GET /orders)
- ✅ Get order details (GET /orders/:id)
- ✅ Update order status (PATCH /orders/:id/status)
- ✅ Order lifecycle (DRAFT → CONFIRMED → PREPARING → READY → COMPLETED/CANCELLED/VOID)
- ✅ Auto-create KDS tickets when PREPARING
- ✅ Auto-generate receipt when COMPLETED
- ✅ Auto-earn loyalty points when COMPLETED
- ✅ Apply promotions during create
- ✅ Order items with quantities
- ✅ Order discounts tracking

**Database**:
```prisma
model Order {
  id              String            @id @default(cuid())
  orderNo         String            @unique
  branchId        String
  customerId      String?
  status          OrderStatus
  subtotal        Decimal
  discount        Decimal           @default(0)
  tax             Decimal
  total           Decimal
  paymentMethod   PaymentMethod?
  loyaltyEarned   Int?
  createdAt       DateTime          @default(now())
  updatedAt       DateTime          @updatedAt

  // Relations
  branch          Branch            @relation(fields: [branchId], references: [id])
  customer        Customer?         @relation(fields: [customerId], references: [id])
  items           OrderItem[]
  discounts       OrderDiscount[]
  payments        Payment[]

  // Indexes
  @@index([branchId, createdAt])
  @@index([customerId])
  @@index([orderNo])
}

model OrderItem {
  id              String            @id @default(cuid())
  orderId         String
  menuItemId      String
  quantity        Int
  unitPrice       Decimal
  subtotal        Decimal

  order           Order             @relation(fields: [orderId], references: [id])
  menuItem        MenuItem          @relation(fields: [menuItemId], references: [id])

  @@index([orderId])
}
```

**Files**:
- `orders/orders.module.ts`
- `orders/orders.service.ts` (449 lines)
- `orders/orders.controller.ts`
- `orders/dto/create-order.dto.ts`

---

### ❌ Missing (20% Gap)

**Advanced POS Features**:
1. **Split Bill** (0%)
   - Split by items
   - Split by amount
   - Split by percentage
   - Multiple payment methods per order

2. **Multi-Tender** (0%)
   - Pay with cash + card
   - Pay with points + cash
   - Multiple payment records per order

3. **Refund/Void** (0%)
   - Endpoint: POST /orders/:id/refund
   - Endpoint: POST /orders/:id/void
   - Fields: refund_reason, void_reason, refunded_by
   - Audit trail
   - Reverse loyalty points
   - Reverse inventory

4. **Reason Codes** (0%)
   - When override price
   - When apply discount
   - Manager approval required

5. **Cash Management** (0%)
   - Open/close cash drawer
   - Z report (end of day)
   - X report (mid-day)
   - Cash session tracking
   - Database: `cash_sessions` table

---

### 🔧 Priority Actions

**Phase 1 (Week 3-4)**: Complete orders module
1. Implement split bill (2 days)
2. Implement multi-tender (2 days)
3. Implement refund/void (3 days)
4. Add reason codes (1 day)
5. Add cash management (2 days)

**Estimated Effort**: 2 weeks

---

## 🟢 4. PAYMENTS MODULE (90% Complete)

**Status**: Excellent security, missing reconciliation

### ✅ Implemented

**MoMo Integration**:
- ✅ Create payment (POST /payments/ewallet/momo/create)
- ✅ IPN webhook handler (POST /payments/ewallet/momo/ipn)
- ✅ Get payment status (GET /payments/:extref/status)
- ✅ 5-layer security (EXCELLENT!):
  1. HMAC verification
  2. Timestamp validation (5 min window)
  3. Redis nonce anti-replay
  4. Database event deduplication
  5. Atomic transaction

**Database**:
```prisma
model Payment {
  id              String            @id @default(cuid())
  orderId         String
  amount          Decimal
  gateway         String            // 'momo', 'zalopay', 'bank_qr', 'cash'
  externalRef     String            @unique
  status          PaymentStatus
  metadata        Json?
  createdAt       DateTime          @default(now())
  updatedAt       DateTime          @updatedAt

  order           Order             @relation(fields: [orderId], references: [id])

  @@index([externalRef])
  @@index([status])
}

model PaymentEvent {
  id              String            @id @default(cuid())
  eventId         String            @unique  // For deduplication
  paymentId       String
  eventType       String
  eventData       Json
  processedAt     DateTime          @default(now())

  @@index([eventId])
}
```

**Files**:
- `payments/payments.module.ts`
- `payments/payments.service.ts` (287 lines)
- `payments/payments.controller.ts`
- `payments/momo.provider.ts`
- `payments/utils/momo-hmac.util.ts`

**Security Highlights**:
```typescript
// payments/payments.service.ts:154-278
async handleMoMoIpn(dto: MoMoIpnDto) {
  // 1. HMAC verification
  const isValid = MoMoHmacUtil.verifySignature(dto, secretKey);
  if (!isValid) throw new UnauthorizedException('Invalid HMAC');

  // 2. Timestamp validation (5 min window)
  const timestamp = dto.requestId.split('-')[0];
  if (Date.now() - timestamp > 300000) {
    throw new BadRequestException('Request expired');
  }

  // 3. Redis nonce anti-replay
  const nonce = `momo:ipn:${dto.requestId}`;
  const exists = await this.redis.get(nonce);
  if (exists) throw new BadRequestException('Duplicate request');
  await this.redis.set(nonce, '1', 'EX', 300);

  // 4. Database event deduplication
  const existing = await this.prisma.paymentEvent.findUnique({
    where: { eventId: dto.requestId },
  });
  if (existing) return { status: 'already_processed' };

  // 5. Atomic transaction
  await this.prisma.$transaction(async (tx) => {
    // Update payment
    await tx.payment.update({
      where: { externalRef: dto.orderId },
      data: { status: 'SUCCEEDED' },
    });

    // Create event
    await tx.paymentEvent.create({
      data: { eventId: dto.requestId, ... },
    });
  });
}
```

**Status**: EXCELLENT implementation, best practice!

---

### ❌ Missing (10% Gap)

1. **Reconciliation** (0%)
   - Endpoint: POST /payments/reconcile
   - D+1 matching (expected vs actual)
   - Database: `reconciliations` table
   - Fields: expected_amount, actual_amount, discrepancy, reconciled_at
   - Alert for mismatches

2. **ZaloPay Integration** (0%)
   - Similar to MoMo
   - 5-layer security
   - IPN webhook

3. **Bank QR Integration** (0%)
   - VietQR standard
   - Dynamic QR generation
   - IPN webhook

---

### 🔧 Priority Actions

**Phase 1 (Week 5)**: Add reconciliation
1. Design reconciliation schema (1 day)
2. Implement reconciliation API (2 days)
3. Add reconciliation report (1 day)
4. Add alerts for discrepancies (1 day)

**Phase 2 (Week 6-7)**: Add ZaloPay + Bank QR
1. ZaloPay integration (3 days)
2. Bank QR integration (3 days)
3. Testing (1 day)

**Estimated Effort**: 3 weeks

---

## 🟡 5. PROMOTIONS MODULE (60% Complete) ⭐ DISCOVERED

**Status**: Basic features excellent, missing advanced types

### ✅ Implemented

**Full CRUD**:
- ✅ Create promotion (POST /promotions)
- ✅ List promotions (GET /promotions?activeOnly=true)
- ✅ Get by ID (GET /promotions/:id)
- ✅ Get by code (GET /promotions/code/:code)
- ✅ Update promotion (PATCH /promotions/:id)
- ✅ Delete promotion (DELETE /promotions/:id)
- ✅ Apply promotion (POST /promotions/apply)

**Promotion Types**:
- ✅ PERCENTAGE (with maxDiscount cap)
  ```typescript
  discount = subtotal * (percentage / 100);
  if (maxDiscount) discount = Math.min(discount, maxDiscount);
  ```
- ✅ FIXED_AMOUNT (doesn't exceed order total)
  ```typescript
  discount = Math.min(fixedAmount, subtotal);
  ```
- ⚠️ BUY_X_GET_Y (stubbed, returns 0)
- ⚠️ COMBO_PRICE (stubbed, returns 0)

**Validation Logic**:
- ✅ Status check (ACTIVE/SCHEDULED/EXPIRED)
- ✅ Date range validation
- ✅ Minimum order value
- ✅ Usage limit enforcement
- ✅ Code uniqueness constraint
- ✅ Auto-status transitions

**Files**:
- `promotions/promotions.service.ts` (296 lines)
- `promotions/promotions.controller.ts` (99 lines)
- `promotions/dto/create-promotion.dto.ts`
- `promotions/dto/apply-promotion.dto.ts`

**Integration**:
```typescript
// orders/orders.service.ts:164-223
async applyPromotion(order: Order, promotionCode: string) {
  const result = await this.promotions.applyPromotion({
    code: promotionCode,
    subtotal: order.subtotal,
    items: order.items,
  });

  if (result.valid) {
    order.discount = result.discount;
    // Save to OrderDiscount table
  }
}
```

---

### ❌ Missing (40% Gap)

1. **BUY_X_GET_Y Logic** (0%)
   - Parse rules: "buy 2 coffee, get 1 free"
   - Match items by SKU/category
   - Calculate discount (cheapest free or most expensive free)
   - Example: Buy 2 Latte → 3rd Latte free

2. **COMBO_PRICE Logic** (0%)
   - Define bundles: "1 coffee + 1 cake = 50k"
   - Match bundle items in order
   - Apply combo pricing
   - Handle partial matches

3. **Time-Based Promotions** (0%)
   - Golden hour: "2-4pm happy hour, 20% off"
   - Day-of-week: "Monday special"
   - Schedule validation in applyPromotion()

4. **Promotion Simulator** (0%)
   - Endpoint: POST /promotions/simulate
   - Test against past orders (last 30 days)
   - Return: potential discount, uplift %, orders affected

5. **Hold-out Groups (A/B Testing)** (0%)
   - Define control group (no promotion)
   - Define treatment group (with promotion)
   - Random assignment (50/50)
   - Statistical significance calculation
   - Database: `promotion_experiments` table

6. **Priority System** (0%)
   - When multiple promotions apply, pick best
   - Configurable priority rules
   - Anti double-dip enforcement

7. **Budget Cap** (0%)
   - Stop promotion when budget exhausted
   - Database: `promotions.budget_used` field
   - Alert when 80% used

8. **Frequency Cap** (0%)
   - Limit usage per customer per period
   - Example: "1 use per customer per day"
   - Database: `promotion_usages` table

---

### 🔧 Priority Actions

**Phase 1 (Week 3)**: Advanced types
1. Implement BUY_X_GET_Y (2 days)
2. Implement COMBO_PRICE (2 days)
3. Add time-based promotions (1 day)

**Phase 1 (Week 4)**: Analytics
1. Build simulator (2 days)
2. Build A/B testing framework (2 days)
3. Add priority system (1 day)

**Estimated Effort**: 2 weeks

---

## 🟡 6. REPORTS/KPIs MODULE (50% Complete) ⭐ DISCOVERED

**Status**: Core reports excellent, missing advanced analytics

### ✅ Implemented (6 Reports)

**1. Daily Sales Report** (GET /reports/daily-sales)
- Total orders (completed count)
- Total revenue (after discount + tax)
- Gross revenue (before discount)
- Total discount given
- Total tax collected
- Average Order Value (AOV)
- Total successful payments

**2. Top Selling Items** (GET /reports/top-selling)
- Menu item name, category
- Quantity sold
- Revenue
- Order count
- Top 10 by default

**3. Inventory Movements** (GET /reports/inventory-movements)
- Summary by type (IN/OUT/ADJUST/TRANSFER)
- Count per type
- Total quantity moved
- Low stock items (currentStock ≤ minStock)

**4. Promotion Analytics** (GET /reports/promotion-analytics)
- Promotion code, name
- Usage count
- Total discount given
- Average discount per use

**5. Revenue by Category** (GET /reports/revenue-by-category)
- Category name
- Revenue per category
- Items sold
- Order count

**6. Customer Analytics** (GET /reports/customer-analytics)
- Total customers
- New customers (in period)
- Top 10 customers by spend
- Customer lifetime value

**Files**:
- `reports/reports.service.ts` (432 lines)
- `reports/reports.controller.ts` (141 lines)

---

### ❌ Missing (50% Gap)

1. **Contribution Margin Reports** (0%)
   - Calculate COGS from BOM
   - Formula: Revenue - COGS = CM
   - CM % by item/category
   - Endpoint: GET /reports/contribution-margin

2. **Promo Uplift Analysis** (0%)
   - Compare orders with vs without promotion
   - Uplift % = (Treatment - Control) / Control * 100
   - Incremental revenue
   - ROI per promotion
   - Endpoint: GET /reports/promotion-uplift

3. **Labor Reports** (0%)
   - Hours worked (from attendance)
   - Labor cost = hours × hourly_rate
   - Revenue per labor hour
   - Productivity metrics
   - Endpoint: GET /reports/labor

4. **Device Health Reports** (0%)
   - Printer uptime %
   - KDS response time
   - Device heartbeat status
   - Endpoint: GET /reports/devices

5. **Payment Success Rate** (0%)
   - Success rate by gateway
   - Average processing time
   - Failed payment reasons
   - Endpoint: GET /reports/payments

6. **Reconciliation Status** (0%)
   - D+1 matching
   - Discrepancies table
   - Endpoint: GET /reports/reconciliation

7. **Loyalty Reports** (0%) ⚠️ CRITICAL
   - README Line 321 requires GET /reports/loyalty
   - Earned/redeemed/expired points
   - Active members
   - Tiers distribution
   - CLV (Customer Lifetime Value)
   - Repeat purchase rate

---

### 🔧 Priority Actions

**Phase 1 (Week 5)**: Advanced analytics
1. Contribution Margin (2 days)
2. Promo Uplift (2 days)
3. Device Health (1 day)

**Phase 1 (Week 6)**: Labor & Payments
1. Labor Reports (2 days)
2. Payment Success Rate (1 day)
3. Reconciliation Status (2 days)
4. Loyalty Reports (2 days) ⚠️ HIGH PRIORITY

**Estimated Effort**: 2 weeks

---

## 🟡 7. LOYALTY MODULE (40% Complete) ⬇️ UPDATED

**Status**: Basic earn/redeem working, missing 60% of features

### ✅ Implemented

**Core Features**:
- ✅ Earn points (POST /loyalty/earn)
- ✅ Redeem points (POST /loyalty/redeem) with balance check
- ✅ Adjust points (POST /loyalty/adjust) - Manual
- ✅ Update tier (POST /loyalty/tier) - Manual
- ✅ Get account (GET /loyalty/:customerId)
- ✅ Get transactions (GET /loyalty/:customerId/transactions)
- ✅ Get balance (GET /loyalty/:customerId/balance)

**Auto-Integration**:
```typescript
// orders/orders.service.ts:372-398
async completeOrder(orderId: string) {
  // Auto-earn points: 1 point per 10k VND
  const points = Math.floor(order.total / 10000);

  await this.loyalty.earnPoints(order.customerId, {
    points,
    orderId,
    description: `Order #${order.orderNo}`,
  });

  // Update order
  await this.prisma.order.update({
    where: { id: orderId },
    data: { loyaltyEarned: points },
  });
}
```

**Database**:
```prisma
model LoyaltyAccount {
  id          String   @id @default(cuid())
  customerId  String   @unique
  balance     Int      @default(0)
  tier        String   @default("bronze") // bronze, silver, gold, platinum
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  customer    Customer @relation(fields: [customerId], references: [id])
}

model LoyaltyTransaction {
  id          String   @id @default(cuid())
  accountId   String
  type        String   // 'earn', 'redeem', 'adjust', 'expire'
  points      Int
  orderId     String?
  description String?
  createdAt   DateTime @default(now())

  account     LoyaltyAccount @relation(fields: [accountId], references: [id])
}
```

**Files**:
- `loyalty/loyalty.service.ts` (163 lines)
- `loyalty/loyalty.controller.ts`
- `loyalty/dto/earn-points.dto.ts`

---

### ❌ Missing (60% Gap) ⚠️ CRITICAL

1. **Gift Card System** (0%) ⚠️ HIGH PRIORITY
   - POST /gift-cards (issue)
   - POST /gift-cards/{code}/redeem
   - GET /gift-cards/{code}/balance
   - POST /gift-cards/{code}/transfer
   - Database: gift_cards, gift_card_transactions

2. **Referral Program** (0%)
   - Generate referral code
   - Apply referral code
   - Bonus: Referrer +100 pts, Referee +50 pts
   - Database: referral_codes, referrals

3. **Points Expiry** (0%) ⚠️ CRITICAL!
   - **README Line 410**: "nhắc hết hạn điểm hoạt động"
   - Points expire after 365 days
   - Scheduled job: Send reminders (30 days before)
   - Scheduled job: Auto-expire old points
   - CRM integration: Zalo OA/SMS/Email reminders
   - Database: Add expires_at, expired to loyalty_transactions

4. **Loyalty Reports** (0%) ⚠️ CRITICAL!
   - **README Line 321**: GET /reports/loyalty
   - **README Line 335** KPIs:
     - earned/redeemed/expired
     - active members
     - tiers distribution
     - CLV (Customer Lifetime Value)
     - repeat purchase rate
   - Currently: NO loyalty reports

5. **Auto Tier Upgrade** (0%)
   - Bronze: 0 spend
   - Silver: 1M VND or 500 points
   - Gold: 5M VND or 2500 points
   - Platinum: 20M VND or 10000 points
   - Trigger: After order completion, nightly job
   - Send upgrade notification

---

### 🔧 Priority Actions

**Phase 1 (Week 8-9)**: Gift Card + Referral + Auto Tier
1. Gift Card system (3 days)
2. Referral program (2 days)
3. Auto Tier Upgrade (2 days)
4. Testing (1 day)

**Phase 1 (Week 10)**: Points Expiry + Reports
1. Points Expiry logic (2 days)
2. Expiry reminders (1 day)
3. Loyalty Reports (2 days) ⚠️ HIGH PRIORITY
4. CLV + Repeat Rate calculations (1 day)

**Estimated Effort**: 3 weeks

---

[Continue with other modules: Inventory, Menu, KDS, etc...]

---

## 📊 SUMMARY TABLE

| Module | Current | Target | Gap | Effort |
|--------|---------|--------|-----|--------|
| Backend Core | 100% | 100% | 0% | - |
| Authentication | 100% | 100% | 0% | - |
| Orders | 80% | 100% | 20% | 2w |
| Payments | 90% | 100% | 10% | 3w |
| Promotions | 60% | 90% | 30% | 2w |
| Reports | 50% | 80% | 30% | 2w |
| Loyalty | 40% | 70% | 30% | 3w |
| Inventory | 40% | 80% | 40% | 4w |
| Menu | 40% | 80% | 40% | 2w |
| KDS | 60% | 80% | 20% | 1w |
| Other | 70% | 80% | 10% | 1w |

**Total Backend Effort**: ~20 weeks (Phase 0 + Phase 1)

---

**Last Updated**: 2025-11-06
**Next Review**: After each module completion
