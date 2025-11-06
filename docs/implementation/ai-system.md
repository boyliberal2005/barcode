# AI SYSTEM DEEP DIVE

**Status**: 0% → Target 80%
**Timeline**: 22-28 weeks (Phases 2A-2E)
**Last Updated**: 2025-11-06

---

## 🎯 OVERVIEW

The AI system is **70% of what makes this system "smart"**. Without AI, this is just a normal POS.

### 7 Major AI Components

| Component | Business Impact | Complexity | Priority | Weeks |
|-----------|----------------|------------|----------|-------|
| **1. FaceID Recognition** | Critical ⭐⭐⭐⭐⭐ | High | P0 | 5 |
| **2. Voice AI (STT/NLU/TTS)** | Critical ⭐⭐⭐⭐⭐ | High | P0 | 8 |
| **3. PromptOps** | High ⭐⭐⭐⭐ | Medium | P1 | 2 |
| **4. Demand Forecasting** | High ⭐⭐⭐⭐ | Medium | P1 | 4 |
| **5. Upsell/Recommend** | Medium ⭐⭐⭐ | Medium | P2 | 3 |
| **6. Workforce Scheduling** | Medium ⭐⭐⭐ | Medium | P2 | 4 |
| **7. Anomaly Detection** | Medium ⭐⭐⭐ | Low | P2 | 2 |

**Total Estimated Effort**: 22-28 weeks

---

## 🔴 1. FACEID RECOGNITION (Phase 2A - 5 weeks) ⭐ HIGHEST PRIORITY

### Why This Matters

**Business Impact**: THE core differentiator
- **Customer Experience**: "Xin chào anh Nam! Anh uống Latte như mọi khi không?" (personalized greeting)
- **Loyalty Integration**: Auto-lookup points, tier, purchase history
- **Upsell**: Recommend based on preferences
- **Opt-in Rate**: Target > 60% of customers

**Without FaceID**: This is just a normal POS with QR code loyalty. Not "smart".

---

### Technical Architecture

```
┌─────────────┐
│   Camera    │
│  (1080p)    │
└──────┬──────┘
       │ Image (RGB)
       ▼
┌─────────────────────────────────────────────┐
│  YuNet Face Detector (ONNX)                 │
│  - Bounding box (x, y, w, h)                │
│  - 5 landmarks (eyes, nose, mouth corners)  │
│  - Confidence score                         │
│  - Target: < 100ms p95                      │
└──────┬──────────────────────────────────────┘
       │ Face ROI + Landmarks
       ▼
┌─────────────────────────────────────────────┐
│  5-Point Alignment                          │
│  - Affine transform to canonical pose       │
│  - Crop to 112x112                          │
│  - Normalize pixels [0, 1]                  │
└──────┬──────────────────────────────────────┘
       │ Aligned Face
       ▼
┌─────────────────────────────────────────────┐
│  Embedder (MobileFaceNet or ArcFace)        │
│  - 128-dim embedding vector                 │
│  - L2 normalization                         │
│  - Target: < 100ms p95                      │
└──────┬──────────────────────────────────────┘
       │ Embedding (128-dim)
       ▼
┌─────────────────────────────────────────────┐
│  pgvector Similarity Search                 │
│  - Cosine similarity (IVFFlat or HNSW)      │
│  - Threshold: 0.75-0.80 (profile-dependent) │
│  - Target: < 100ms p95                      │
└──────┬──────────────────────────────────────┘
       │
       ├─> MATCH ──> customer_id
       │             ├─> Loyalty Account
       │             ├─> Purchase History
       │             ├─> Personalized Recommendations
       │             └─> TTS Greeting
       │
       └─> NO MATCH ──> Prompt Opt-in
                        └─> Register Face
```

**Total Latency Target**: < 300ms p95

---

### 3 Performance Profiles

| Profile | Model | Threshold | Liveness | Use Case |
|---------|-------|-----------|----------|----------|
| **Lite** | MobileFaceNet int8 | 0.75 | ❌ No | Fast food, high throughput |
| **Balanced** ⭐ | ArcFace R50 int8 | 0.78 | ✅ Yes | Recommended for cafe |
| **Max** | ArcFace R100 fp16 | 0.80 | ✅ Yes | High security, VIP |

**Recommendation**: Start with **Balanced** profile.

---

### Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Face embeddings table
CREATE TABLE face_embeddings (
  customer_id uuid PRIMARY KEY REFERENCES customers(id),
  embedding vector(128) NOT NULL,
  enc_method text DEFAULT 'aes-256-gcm',
  profile text CHECK (profile IN ('lite', 'balanced', 'max')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- IVFFlat index for fast search (good for < 100k faces)
CREATE INDEX idx_face_embeddings_vec
  ON face_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- For scale > 100k faces, use HNSW:
-- CREATE INDEX idx_face_embeddings_hnsw
--   ON face_embeddings USING hnsw (embedding vector_cosine_ops)
--   WITH (m = 16, ef_construction = 64);

-- Consent tracking (GDPR)
CREATE TABLE customer_consents (
  customer_id uuid REFERENCES customers(id),
  consent_type text CHECK (consent_type IN ('faceid', 'sms', 'email', 'zalo')),
  granted boolean NOT NULL,
  granted_at timestamptz,
  revoked_at timestamptz,
  PRIMARY KEY (customer_id, consent_type)
);

-- Audit log
CREATE TABLE face_access_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid REFERENCES customers(id),
  action text CHECK (action IN ('recognize', 'register', 'delete')),
  confidence numeric(5, 4),
  ip_address inet,
  user_agent text,
  created_at timestamptz DEFAULT now()
);
```

---

### API Endpoints

#### 1. POST /face/recognize

**Request**:
```typescript
interface RecognizeRequest {
  image: string; // base64-encoded RGB image
  profile?: 'lite' | 'balanced' | 'max'; // default: balanced
  includeRecommendations?: boolean; // default: true
}
```

**Response**:
```typescript
interface RecognizeResponse {
  matched: boolean;
  customerId?: string;
  confidence?: number; // 0.0-1.0
  profile: string;
  latency: {
    detection: number; // ms
    embedding: number; // ms
    search: number; // ms
    total: number; // ms
  };
  loyalty?: {
    points: number;
    tier: 'bronze' | 'silver' | 'gold' | 'platinum';
    nextTierPoints: number;
  };
  recommendations?: MenuItem[];
  greeting?: string; // for TTS: "Xin chào anh Nam!"
}
```

**Example**:
```json
{
  "matched": true,
  "customerId": "uuid-123",
  "confidence": 0.87,
  "profile": "balanced",
  "latency": {
    "detection": 85,
    "embedding": 92,
    "search": 78,
    "total": 255
  },
  "loyalty": {
    "points": 1250,
    "tier": "silver",
    "nextTierPoints": 250
  },
  "recommendations": [
    { "id": "item-1", "name": "Caramel Latte", "price": 55000, "reason": "Your favorite" },
    { "id": "item-2", "name": "Cheesecake", "price": 45000, "reason": "Pairs well" }
  ],
  "greeting": "Xin chào anh Nam! Anh uống Latte như mọi khi không?"
}
```

---

#### 2. POST /customers/:id/face/register

**Request**:
```typescript
interface RegisterRequest {
  image: string; // base64
  profile?: 'lite' | 'balanced' | 'max';
  consent: boolean; // must be true
}
```

**Response**:
```typescript
interface RegisterResponse {
  success: boolean;
  customerId: string;
  message: string;
}
```

**Flow**:
1. Check consent granted (must be true)
2. Extract embedding from image
3. Encrypt embedding (AES-256-GCM)
4. Store in `face_embeddings` table
5. Log to `face_access_log`

---

#### 3. DELETE /customers/:id/face/delete

**GDPR Right to Be Forgotten**

**Request**: None (just customer ID in path)

**Response**:
```typescript
interface DeleteResponse {
  success: boolean;
  message: string;
  deletedAt: string;
}
```

**Flow**:
1. Delete from `face_embeddings`
2. Revoke consent in `customer_consents`
3. Log to `face_access_log`
4. Anonymize historical logs (GDPR requirement)

---

### Privacy & Security

#### 1. Opt-in Consent (GDPR)

**Consent Flow**:
```
Customer approaches kiosk
   ↓
FaceID: NO MATCH
   ↓
Display: "Đăng ký FaceID để đặt hàng nhanh hơn?"
   [Đồng ý]  [Không, cảm ơn]
   ↓
If [Đồng ý]:
   Show consent terms
   ↓
   Capture face image
   ↓
   Register embedding
   ↓
   Next visit: Auto-recognize!
```

**Consent Storage**:
```sql
INSERT INTO customer_consents (customer_id, consent_type, granted, granted_at)
VALUES ('uuid-123', 'faceid', true, now());
```

---

#### 2. Encryption (AES-256-GCM)

**Why**: Embeddings are biometric data (GDPR Article 9)

**Implementation**:
```typescript
import crypto from 'crypto';

export class FaceEmbeddingCrypto {
  private key: Buffer; // 32 bytes from env

  constructor() {
    this.key = Buffer.from(process.env.FACE_ENCRYPTION_KEY, 'hex');
  }

  encrypt(embedding: number[]): Buffer {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-gcm', this.key, iv);

    const plaintext = Buffer.from(new Float32Array(embedding).buffer);
    const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
    const authTag = cipher.getAuthTag();

    // Format: [IV (16 bytes)] [Auth Tag (16 bytes)] [Ciphertext]
    return Buffer.concat([iv, authTag, encrypted]);
  }

  decrypt(encrypted: Buffer): number[] {
    const iv = encrypted.slice(0, 16);
    const authTag = encrypted.slice(16, 32);
    const ciphertext = encrypted.slice(32);

    const decipher = crypto.createDecipheriv('aes-256-gcm', this.key, iv);
    decipher.setAuthTag(authTag);

    const plaintext = Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);

    return Array.from(new Float32Array(plaintext.buffer));
  }
}
```

**Key Management**:
- Store in AWS Secrets Manager or similar
- Rotate every 90 days
- Use different keys per environment

---

#### 3. Audit Logging

**Log Every Access**:
```typescript
await this.prisma.faceAccessLog.create({
  data: {
    customerId,
    action: 'recognize',
    confidence: 0.87,
    ipAddress: req.ip,
    userAgent: req.headers['user-agent'],
  },
});
```

**Required for**:
- GDPR compliance (audit trail)
- Security investigations
- Fraud detection

---

### Performance Benchmarks

**Target SLO**:
| Metric | Target | Measurement |
|--------|--------|-------------|
| Face detection | < 100ms p95 | YuNet inference |
| Embedding extraction | < 100ms p95 | ArcFace inference |
| Vector search | < 100ms p95 | pgvector query |
| **Total latency** | < 300ms p95 | End-to-end |
| False Accept Rate | < 0.01% | Match when NOT same person |
| False Reject Rate | < 1% | NO match when IS same person |

**How to Measure**:
```typescript
const start = Date.now();

// Detection
const detectionStart = Date.now();
const faces = await this.detector.detect(image);
const detectionTime = Date.now() - detectionStart;

// Embedding
const embeddingStart = Date.now();
const embedding = await this.embedder.extract(faces[0]);
const embeddingTime = Date.now() - embeddingStart;

// Search
const searchStart = Date.now();
const match = await this.search(embedding);
const searchTime = Date.now() - searchStart;

const totalTime = Date.now() - start;

// Log to Prometheus
this.metrics.faceDetectionDuration.observe(detectionTime);
this.metrics.faceEmbeddingDuration.observe(embeddingTime);
this.metrics.faceSearchDuration.observe(searchTime);
this.metrics.faceRecognitionTotal.observe(totalTime);
```

---

### Testing Strategy

**1. Unit Tests**:
- Face detection accuracy (test images)
- Embedding consistency (same face → same embedding)
- Encryption/decryption round-trip

**2. Integration Tests**:
- End-to-end flow: image → customer_id
- Consent flow
- Delete flow

**3. Performance Tests**:
- Latency under load (100 RPS)
- Memory usage (model size)
- Concurrent requests (thread safety)

**4. Accuracy Tests**:
- False Accept Rate: 1000 different face pairs → should NOT match
- False Reject Rate: 1000 same face pairs → should match

---

### Deployment

**Infrastructure**:
- CPU: 4+ cores (ONNX Runtime uses all cores)
- RAM: 4GB+ (models + embeddings cache)
- GPU: Optional (TensorRT for 3x speedup)

**Docker Image**:
```dockerfile
FROM node:18-slim

# Install ONNX Runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy models
COPY models/ /app/models/

# Copy app
COPY . /app
WORKDIR /app

RUN pnpm install --prod
RUN pnpm build

CMD ["node", "dist/main.js"]
```

---

### Monitoring & Alerts

**Metrics to Track**:
- `face_recognition_latency_ms{percentile="p95"}` < 300
- `face_detection_latency_ms{percentile="p95"}` < 100
- `face_embedding_latency_ms{percentile="p95"}` < 100
- `face_search_latency_ms{percentile="p95"}` < 100
- `face_false_accept_rate` < 0.0001
- `face_false_reject_rate` < 0.01
- `face_optin_rate` > 0.60

**Alerts**:
- 🔴 P0: Latency > 500ms p95 (affects customer experience)
- 🔴 P0: False Accept Rate > 0.01% (security risk)
- 🟡 P1: False Reject Rate > 2% (poor user experience)
- 🟡 P1: Opt-in rate < 40% (low adoption)

---

### Rollout Plan

**Phase 1 (Week 11-12)**: Internal Testing
- Deploy to staging
- Test with team members (20 faces)
- Tune thresholds
- Fix bugs

**Phase 2 (Week 13)**: Pilot (1 Branch)
- Deploy to 1 branch
- Monitor for 1 week
- Target: 50 customers opt-in
- Measure SLOs

**Phase 3 (Week 14)**: Gradual Rollout
- Deploy to 5 branches
- Monitor for 1 week
- Target: 200 customers opt-in

**Phase 4 (Week 15)**: Full Rollout
- Deploy to all branches
- Marketing campaign: "Đặt hàng nhanh với FaceID!"
- Target: 60% opt-in rate in 3 months

---

## 🔵 2. VOICE AI SYSTEM (Phase 2B - 8 weeks)

### Components

```
┌──────────────────────────────────────────────────┐
│  VOICE AI PIPELINE                               │
├──────────────────────────────────────────────────┤
│                                                  │
│  Microphone → Audio Pipeline → STT → NLU → TTS  │
│               (AEC/VAD/KWS)                      │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 2.1 Audio Pipeline

**WebRTC Processing**:
- **AEC** (Acoustic Echo Cancellation): Remove speaker feedback
- **NS** (Noise Suppression): Remove background noise
- **AGC** (Automatic Gain Control): Normalize volume
- **VAD** (Voice Activity Detection): Detect speech start/end

**Wake-Word Detection**:
- Porcupine (Picovoice): "Xin chào" or custom wake word
- Always-listening mode
- Low CPU usage (< 5%)

**Implementation**:
```typescript
import Porcupine from '@picovoice/porcupine-node';

const porcupine = new Porcupine(
  accessKey,
  [Porcupine.KEYWORDS.HEY_GOOGLE], // or custom
  [0.5], // sensitivity
);

// In audio worklet
const keyword = porcupine.process(audioFrame);
if (keyword >= 0) {
  this.emit('wake-word-detected');
  // Start STT
}
```

---

### 2.2 STT (Speech-to-Text)

**Options**:

| Provider | Accuracy | Latency | Cost | Vietnamese Support |
|----------|----------|---------|------|-------------------|
| **Google Cloud STT** | Excellent | Low | $$$ | ✅ Excellent |
| **Azure Speech** | Excellent | Low | $$$ | ✅ Good |
| **FPT.AI** | Good | Medium | $$ | ✅ Excellent (local) |
| **Whisper (local)** | Good | High | Free | ✅ Good |

**Recommendation**: Google Cloud STT + Whisper fallback

**Implementation**:
```typescript
import speech from '@google-cloud/speech';

const client = new speech.SpeechClient();

const request = {
  config: {
    encoding: 'LINEAR16',
    sampleRateHertz: 16000,
    languageCode: 'vi-VN',
    model: 'latest_short',
    enableAutomaticPunctuation: true,
    enableWordTimeOffsets: true,
  },
  interimResults: true, // Partial transcripts
};

const recognizeStream = client
  .streamingRecognize(request)
  .on('data', (data) => {
    const result = data.results[0];
    const transcript = result.alternatives[0].transcript;

    if (result.isFinal) {
      this.emit('final-transcript', transcript);
    } else {
      this.emit('partial-transcript', transcript);
    }
  });

// Pipe audio
audioStream.pipe(recognizeStream);
```

**SLO**:
- First partial transcript: < 400ms
- Final transcript: < 2s (after speech ends)
- Accuracy: > 95% (Vietnamese cafe domain)

---

### 2.3 NLU (Natural Language Understanding)

**Task**: Parse order from speech

**Input**: "Cho mình một ly Latte size lớn và một cái bánh Cheesecake"

**Output**:
```json
{
  "items": [
    {
      "name": "Latte",
      "quantity": 1,
      "size": "L",
      "modifiers": []
    },
    {
      "name": "Cheesecake",
      "quantity": 1,
      "size": null,
      "modifiers": []
    }
  ],
  "confidence": 0.92,
  "clarification": null
}
```

**Model Options**:
1. **GPT-4** (OpenAI) - Best accuracy, high cost
2. **Grok-1** (xAI) - Fast, competitive
3. **Gemini Pro** (Google) - Good accuracy, low cost

**Implementation**:
```typescript
const prompt = `
Bạn là nhân viên order tại quán cafe. Parse order từ câu nói của khách.

Menu:
${JSON.stringify(menuItems)}

Câu nói: "${transcript}"

Trả về JSON:
{
  "items": [{ "name": string, "quantity": number, "size": "S|M|L", "modifiers": string[] }],
  "confidence": number,
  "clarification": string | null
}

Nếu không chắc chắn, set confidence < 0.7 và hỏi lại trong clarification.
`;

const response = await openai.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'system', content: prompt }],
  temperature: 0.1,
  max_tokens: 500,
});

const parsed = JSON.parse(response.choices[0].message.content);
```

**Guardrails**:
- Timeout: 5s max
- Retry: 2 attempts
- Fallback: Keyword matching (if AI fails)
- Cache: Redis (10-30 min TTL)

---

### 2.4 PromptOps (CRITICAL!)

**Why**: Control AI behavior without code changes

**Features**:
1. **Persona Presets** (vui vẻ, lịch sự, hài hước, chuyên nghiệp)
2. **Tone Sliders** (formal ↔ casual)
3. **Context Packs** (menu, promos, loyalty tiers)
4. **A/B Testing** (test multiple prompt versions)
5. **Rollout** (gradual deployment 10% → 50% → 100%)
6. **Kill-Switch** (emergency disable AI)
7. **Guardrails** (content filtering, safety checks)

**Database Schema**:
```sql
CREATE TABLE ai_prompts (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  version text NOT NULL,
  model text CHECK (model IN ('gpt-4', 'grok-1', 'gemini-pro')),
  persona text CHECK (persona IN ('friendly', 'formal', 'humorous', 'professional')),
  system_prompt text NOT NULL,
  context_packs jsonb, -- menu, promos, loyalty
  status text CHECK (status IN ('draft', 'testing', 'active', 'disabled')),
  rollout_percent int DEFAULT 0, -- 0-100%
  created_at timestamptz DEFAULT now()
);

CREATE TABLE ai_prompt_sessions (
  id uuid PRIMARY KEY,
  prompt_id uuid REFERENCES ai_prompts(id),
  customer_id uuid REFERENCES customers(id),
  transcript text,
  nlu_result jsonb,
  success boolean,
  latency_ms int,
  created_at timestamptz DEFAULT now()
);
```

**Example Personas**:
```typescript
const PERSONA_PRESETS = {
  friendly: {
    systemPrompt: 'Bạn là nhân viên order cafe thân thiện, nhiệt tình. Luôn vui vẻ và gần gũi.',
    tone: 'casual',
    examples: [
      { user: 'Cho mình 1 cafe', ai: 'Dạ vâng! Bạn uống cafe gì ạ? Latte hay Americano? 😊' }
    ]
  },
  formal: {
    systemPrompt: 'Bạn là nhân viên order cafe lịch sự, chuyên nghiệp.',
    tone: 'formal',
    examples: [
      { user: 'Cho mình 1 cafe', ai: 'Kính chào quý khách. Quý khách vui lòng cho biết loại cafe?' }
    ]
  }
};
```

**API Endpoints**:
- `GET /ai/prompts/presets` - List personas
- `POST /ai/prompts/deploy` - Deploy new version
- `GET /ai/prompts/sessions` - A/B test results
- `POST /ai/prompts/kill-switch` - Emergency disable

---

### 2.5 TTS (Text-to-Speech)

**Options**:
- **Edge TTS** (Microsoft): Free, good quality, Vietnamese
- **Google Cloud TTS**: Best quality, paid
- **FPT.AI**: Local, Vietnamese-optimized

**Implementation**:
```typescript
import edge from 'edge-tts';

const tts = new edge.Communicate({
  text: 'Xin chào anh Nam! Anh uống Latte như mọi khi không?',
  voice: 'vi-VN-HoaiMyNeural', // Female voice
  rate: '+0%',
  pitch: '+0Hz',
});

const audioStream = await tts.stream();
// Send to WebSocket → Frontend plays audio
```

**SLO**:
- TTS start latency: < 800ms
- Barge-in stop latency: < 200ms (when user speaks)

---

## 🟢 3. DEMAND FORECASTING (Phase 2C - 4 weeks)

[Detailed forecasting implementation...]

---

## 🟣 4. UPSELL/RECOMMEND ENGINE (Phase 2D - 3 weeks)

[Detailed recommendation implementation...]

---

## 🟤 5. WORKFORCE SCHEDULING (Phase 2E - 4 weeks)

[Detailed workforce implementation...]

---

## 🟠 6. ANOMALY DETECTION (Phase 2D - 2 weeks)

[Detailed anomaly detection implementation...]

---

## 📊 AI SYSTEM MONITORING

**Key Metrics**:
- `ai_stt_latency_ms{percentile="p95"}` < 400
- `ai_nlu_latency_ms{percentile="p95"}` < 5000
- `ai_tts_latency_ms{percentile="p95"}` < 800
- `ai_nlu_accuracy` > 0.95
- `ai_wake_word_false_positive_rate` < 0.01
- `face_recognition_latency_ms{percentile="p95"}` < 300

**Dashboard**: Grafana with AI metrics panel

---

**Last Updated**: 2025-11-06
**Next Review**: After each AI component completion
