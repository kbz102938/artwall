# ArtWall 后端工程设计

## 一、技术栈

### 1.1 整体架构：Next.js + Python + Event-Driven

| 层级 | 技术选型 | GCP 服务 | 说明 |
|-----|---------|----------|------|
| 前端 + API | Next.js 14 (App Router) | Cloud Run | 页面 + API Routes |
| ML 服务 | Python FastAPI | Cloud Run | CLIP embedding 提取 |
| 数据库 | PostgreSQL + pgvector | Cloud SQL | 关系型 + 向量搜索 |
| 消息队列 | - | Cloud Pub/Sub | 活动事件处理 |
| 图片存储 | - | Cloud Storage | 画作、用户照片 |
| CDN | - | Cloud CDN | 图片加速（可选） |
| 支付 | Stripe | - | 支付处理、Webhook |

### 1.2 GCP 架构图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                  GCP                                      │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                          Cloud Run                                   │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │ │
│  │  │   Next.js App   │    │  Python CLIP    │    │  Event Worker   │  │ │
│  │  │                 │    │  Service        │    │  (Python)       │  │ │
│  │  │  - Frontend     │    │                 │    │                 │  │ │
│  │  │  - API Routes   │    │  /api/embedding │    │  Process Pub/Sub│  │ │
│  │  └────────┬────────┘    └─────────────────┘    └────────┬────────┘  │ │
│  └───────────┼─────────────────────────────────────────────┼───────────┘ │
│              │                                             │             │
│              ▼                                             │             │
│  ┌─────────────────────┐                                   │             │
│  │   Cloud Pub/Sub     │◀──────────────────────────────────┘             │
│  │                     │                                                 │
│  │  Topic: activities  │                                                 │
│  └─────────────────────┘                                                 │
│              │                                                           │
│              ▼                                                           │
│  ┌─────────────────┐         ┌─────────────────┐                        │
│  │   Cloud SQL     │         │ Cloud Storage   │                        │
│  │   (PostgreSQL   │         │    (Bucket)     │                        │
│  │   + pgvector)   │         │                 │                        │
│  └─────────────────┘         │  - paintings/   │                        │
│                              │  - user-rooms/  │                        │
│                              └─────────────────┘                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Service Responsibilities

| Service | Responsibilities |
|---------|------------------|
| **Next.js** | Frontend, API routes, feed generation |
| **Python CLIP** | Embedding generation for images |
| **Event Worker** | Process activity events, update user embeddings |

---

## 二、核心设计理念

### 2.1 Event-Driven Architecture

```
Principle: Log everything, process async, never block user

User Action → POST /api/activity → Pub/Sub → Worker → Update Embedding
                    ↓
              Returns immediately (fast)
```

### 2.2 Embedding-based Recommendations

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  User interactions shape their embedding in vector space        │
│  Similar paintings are found via cosine similarity              │
│                                                                 │
│  Save painting → Move embedding toward that painting            │
│  Hide painting → Move embedding away from that painting         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Continuous Refinement (No "Final Results" Page)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. User selects home style → Initial embedding                 │
│  2. Show infinite feed based on embedding                       │
│  3. Track all user activities (view, save, purchase, etc.)      │
│  4. Update embedding based on activities                        │
│  5. Feed gets more personalized over time                       │
│                                                                 │
│  No quiz. No final page. Just continuous improvement.           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、项目结构

```
artwall/
├── apps/
│   ├── web/                          # Next.js App
│   │   ├── app/
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── onboarding/           # Style selection
│   │   │   ├── feed/                 # Infinite feed
│   │   │   ├── painting/[id]/        # Painting detail
│   │   │   └── api/
│   │   │       ├── activity/         # Log activities
│   │   │       ├── feed/             # Get personalized feed
│   │   │       ├── paintings/        # Painting CRUD
│   │   │       └── admin/            # Admin APIs
│   │   ├── lib/
│   │   │   ├── db.ts                 # Prisma client
│   │   │   ├── pubsub.ts             # Pub/Sub client
│   │   │   ├── storage.ts            # GCS client
│   │   │   └── activity-tracker.ts   # Frontend tracking
│   │   └── ...
│   │
│   ├── clip-service/                 # Python CLIP Service
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   └── services/
│   │   │       └── embedding.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── event-worker/                 # Python Event Worker
│       ├── app/
│       │   ├── main.py
│       │   └── services/
│       │       ├── activity_processor.py
│       │       └── embedding_updater.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── packages/
│   └── config/                       # Shared config
│       ├── styles.ts                 # Pre-computed style embeddings
│       └── constants.ts
│
├── scripts/
│   ├── generate-embeddings.py        # Pre-compute embeddings
│   └── import-paintings.py
│
└── docker-compose.yml
```

---

## 四、数据库设计

### 4.1 Tables

```sql
-- Enable pgvector
CREATE EXTENSION vector;

-- ============================================
-- PAINTINGS (Core Data)
-- ============================================
CREATE TABLE paintings (
    id              VARCHAR(50) PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    title_en        VARCHAR(255),
    artist          VARCHAR(255) NOT NULL,
    artist_en       VARCHAR(255),
    year            INTEGER,
    style           VARCHAR(100),

    image_url       TEXT NOT NULL,
    image_hd_url    TEXT,

    source          VARCHAR(50),
    source_url      TEXT,
    license         VARCHAR(100),

    -- Core: embedding vector (512 dimensions)
    embedding       vector(512) NOT NULL,

    -- Optional tags for filtering
    tags            TEXT[],
    aspect_ratio    VARCHAR(20),

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Vector index for fast similarity search
CREATE INDEX idx_paintings_embedding
ON paintings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- USER PREFERENCES (Embedding State)
-- ============================================
CREATE TABLE user_preferences (
    visitor_id          VARCHAR(100) PRIMARY KEY,
    embedding           vector(512),
    interaction_count   INTEGER DEFAULT 0,
    last_style_codes    TEXT[],           -- Last selected home styles
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- ACTIVITIES (Event Log - Append Only)
-- ============================================
CREATE TABLE activities (
    id              BIGSERIAL PRIMARY KEY,
    visitor_id      VARCHAR(100) NOT NULL,
    session_id      VARCHAR(100),
    event           VARCHAR(50) NOT NULL,
    painting_id     VARCHAR(50),
    position        INTEGER,              -- Position in feed
    source          VARCHAR(50),          -- "feed", "detail", "search"
    metadata        JSONB,                -- Extra data (dwell_time, etc.)
    processed       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_activities_visitor ON activities(visitor_id, created_at DESC);
CREATE INDEX idx_activities_unprocessed ON activities(processed, created_at)
WHERE processed = FALSE;

-- ============================================
-- SHOWN PAINTINGS (Avoid Repeats)
-- ============================================
CREATE TABLE shown_paintings (
    visitor_id      VARCHAR(100),
    painting_id     VARCHAR(50),
    shown_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (visitor_id, painting_id)
);

CREATE INDEX idx_shown_visitor ON shown_paintings(visitor_id);

-- ============================================
-- SAVED PAINTINGS (User Favorites)
-- ============================================
CREATE TABLE saved_paintings (
    visitor_id      VARCHAR(100),
    painting_id     VARCHAR(50),
    saved_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (visitor_id, painting_id)
);

-- ============================================
-- BATCH JOBS (Admin Upload)
-- ============================================
CREATE TABLE batch_jobs (
    id              VARCHAR(50) PRIMARY KEY,
    status          VARCHAR(20) DEFAULT 'pending',
    total           INTEGER DEFAULT 0,
    processed       INTEGER DEFAULT 0,
    failed          INTEGER DEFAULT 0,
    failed_items    JSONB,
    error           VARCHAR(500),
    created_at      TIMESTAMP DEFAULT NOW(),
    completed_at    TIMESTAMP
);

-- ============================================
-- ORDERS (Payment & Fulfillment)
-- ============================================
CREATE TABLE orders (
    id                  VARCHAR(50) PRIMARY KEY,  -- order_xxx
    visitor_id          VARCHAR(100) NOT NULL,

    -- Stripe
    stripe_session_id   VARCHAR(255) UNIQUE,
    stripe_payment_intent VARCHAR(255),

    -- Order Details
    painting_id         VARCHAR(50) NOT NULL REFERENCES paintings(id),
    size                VARCHAR(20) NOT NULL,     -- "40x50", "50x60", "60x80"
    material            VARCHAR(50) DEFAULT 'canvas',  -- canvas, paper, textured
    frame               VARCHAR(50),              -- black, white, wood, none

    -- Pricing (in cents)
    amount              INTEGER NOT NULL,         -- Total amount in cents
    currency            VARCHAR(10) DEFAULT 'cny',

    -- Status
    status              VARCHAR(20) DEFAULT 'pending',
    -- pending → paid → processing → shipped → delivered → completed
    -- pending → expired (if not paid within 30 min)
    -- paid → refunded

    -- Shipping
    shipping_name       VARCHAR(100),
    shipping_phone      VARCHAR(20),
    shipping_address    TEXT,
    shipping_tracking   VARCHAR(100),

    -- Timestamps
    created_at          TIMESTAMP DEFAULT NOW(),
    paid_at             TIMESTAMP,
    shipped_at          TIMESTAMP,
    delivered_at        TIMESTAMP,

    -- Metadata
    metadata            JSONB
);

CREATE INDEX idx_orders_visitor ON orders(visitor_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_stripe_session ON orders(stripe_session_id);
```

### 4.2 No Tables Needed For

| Data | Storage |
|------|---------|
| Home styles (8 options) | Static config in code |
| Style embeddings | Pre-computed in config |
| Quick preference pairs | Static config in code |

---

## 五、Activity Event System

### 5.1 Event Schema

```typescript
interface ActivityEvent {
  visitorId: string
  sessionId: string
  event: ActivityType
  timestamp: number

  // Context
  paintingId?: string
  position?: number
  source?: 'feed' | 'detail' | 'search' | 'saved'

  // Metadata
  metadata?: {
    dwellTimeMs?: number
    scrollDepth?: number
    styleCode?: string
    query?: string
  }
}

type ActivityType =
  | 'impression'       // Painting appeared on screen
  | 'view'             // Viewed > 1 second
  | 'click'            // Clicked to detail
  | 'save'             // Added to favorites
  | 'unsave'           // Removed from favorites
  | 'purchase'         // Bought it
  | 'share'            // Shared
  | 'hide'             // "Don't show this"
  | 'style_select'     // Selected home style
  | 'session_start'    // Opened app
  | 'session_end'      // Left app
```

### 5.2 Signal Weights

| Event | Weight | Description |
|-------|--------|-------------|
| `purchase` | +1.0 | Strongest positive |
| `save` | +0.5 | Strong positive |
| `share` | +0.4 | Positive |
| `click` | +0.2 | Interest |
| `view` (>5s) | +0.3 | Strong interest |
| `view` (3-5s) | +0.2 | Moderate interest |
| `view` (1-3s) | +0.1 | Slight interest |
| `impression` | 0 | Neutral |
| `hide` | -0.5 | Strong negative |
| `unsave` | -0.3 | Negative |

### 5.3 Pub/Sub Configuration

```yaml
# Topic: artwall-activities
# Subscription: artwall-activities-sub

Topic:
  name: artwall-activities
  message_retention_duration: 7d

Subscription:
  name: artwall-activities-sub
  ack_deadline_seconds: 60
  push_config:
    push_endpoint: https://event-worker-xxx.run.app/process
  retry_policy:
    minimum_backoff: 10s
    maximum_backoff: 600s
```

---

## 六、API Design

### 6.1 User APIs

#### POST /api/activity

```
功能：Log user activities (batched)

Request:
{
  "events": [
    {
      "event": "view",
      "paintingId": "painting_001",
      "position": 3,
      "source": "feed",
      "metadata": { "dwellTimeMs": 4500 }
    },
    {
      "event": "save",
      "paintingId": "painting_002"
    }
  ]
}

Response:
{
  "success": true,
  "logged": 2
}

Logic:
1. Validate events
2. Add visitorId, sessionId, timestamp
3. Publish to Pub/Sub
4. Return immediately (don't wait for processing)
```

#### GET /api/feed

```
功能：Get personalized painting feed

Query Params:
  cursor?: string      // Pagination cursor
  limit?: number       // Default 10

Response:
{
  "paintings": [
    {
      "id": "painting_001",
      "title": "星月夜",
      "artist": "梵高",
      "imageUrl": "https://...",
      "similarity": 0.89
    }
  ],
  "nextCursor": "xxx",
  "hasMore": true
}

Logic:
1. Get visitor embedding from user_preferences
2. If no embedding → return cold start feed
3. Get shown_paintings to exclude
4. Vector similarity search
5. Record as shown
6. Return results
```

#### POST /api/onboarding/style

```
功能：Set initial home style preference

Request:
{
  "styleCodes": ["modern", "nordic"]
}

Response:
{
  "success": true,
  "embedding": [0.023, -0.156, ...]  // Optional: return for debugging
}

Logic:
1. Look up pre-computed embeddings for selected styles
2. Average them to create initial user embedding
3. Save to user_preferences
4. Log activity event
```

#### GET /api/paintings/:id

```
功能：Get painting details

Response:
{
  "painting": {
    "id": "painting_001",
    "title": "星月夜",
    "titleEn": "The Starry Night",
    "artist": "梵高",
    "artistEn": "Vincent van Gogh",
    "year": 1889,
    "style": "Post-Impressionism",
    "imageUrl": "https://...",
    "imageHdUrl": "https://...",
    "source": "MoMA",
    "sourceUrl": "https://...",
    "isSaved": true
  }
}
```

#### GET /api/saved

```
功能：Get user's saved paintings

Response:
{
  "paintings": [...],
  "total": 15
}
```

#### POST /api/upload

```
功能：Upload room photo

Request:
  Content-Type: multipart/form-data
  Body: { image: File }

Response:
{
  "imageUrl": "https://storage.../user-rooms/xxx.jpg",
  "embedding": [0.023, -0.156, ...]
}

Logic:
1. Upload to Cloud Storage
2. Call CLIP service to get embedding
3. Update user_preferences (blend with existing embedding)
```

### 6.2 Admin APIs

#### POST /api/admin/paintings/batch

```
功能：Batch upload paintings

Request:
{
  "paintings": [
    {
      "title": "星月夜",
      "artist": "梵高",
      "imageUrl": "https://source-url...",
      ...
    }
  ]
}

Response:
{
  "jobId": "job_abc123",
  "status": "processing",
  "total": 50
}
```

#### GET /api/admin/paintings/batch/:jobId

```
功能：Check batch job status

Response:
{
  "jobId": "job_abc123",
  "status": "completed",
  "total": 50,
  "processed": 48,
  "failed": 2,
  "failedItems": [...]
}
```

### 6.3 Payment APIs (Stripe)

#### POST /api/checkout

```
功能：Create Stripe Checkout session

Request:
{
  "paintingId": "painting_001",
  "size": "60x80",
  "material": "canvas",
  "frame": "black"
}

Response:
{
  "checkoutUrl": "https://checkout.stripe.com/pay/cs_xxx",
  "sessionId": "cs_xxx",
  "orderId": "order_abc123"
}

Logic:
1. Calculate price based on size/material/frame
2. Create order record (status: pending)
3. Create Stripe Checkout session
4. Return checkout URL
```

#### POST /api/webhooks/stripe

```
功能：Handle Stripe webhook events

Headers:
  stripe-signature: xxx

Events handled:
- checkout.session.completed → Mark order as paid
- payment_intent.succeeded → Confirm payment
- payment_intent.payment_failed → Log failure
- charge.refunded → Mark order as refunded

Logic:
1. Verify webhook signature
2. Parse event type
3. Update order status
4. Log activity (purchase event)
5. Send confirmation email (optional)
```

#### GET /api/orders

```
功能：Get user's order history

Response:
{
  "orders": [
    {
      "id": "order_abc123",
      "painting": {
        "id": "painting_001",
        "title": "星月夜",
        "imageUrl": "https://..."
      },
      "size": "60x80",
      "material": "canvas",
      "amount": 29900,
      "status": "shipped",
      "trackingNumber": "SF123456789",
      "createdAt": "2025-01-01T10:00:00Z"
    }
  ]
}
```

#### GET /api/orders/:id

```
功能：Get order details

Response:
{
  "order": {
    "id": "order_abc123",
    "painting": {...},
    "size": "60x80",
    "material": "canvas",
    "frame": "black",
    "amount": 29900,
    "currency": "cny",
    "status": "shipped",
    "shipping": {
      "name": "张三",
      "phone": "13800138000",
      "address": "北京市朝阳区xxx",
      "tracking": "SF123456789"
    },
    "timeline": [
      {"status": "pending", "at": "2025-01-01T10:00:00Z"},
      {"status": "paid", "at": "2025-01-01T10:02:00Z"},
      {"status": "processing", "at": "2025-01-01T12:00:00Z"},
      {"status": "shipped", "at": "2025-01-02T14:00:00Z"}
    ]
  }
}
```

#### POST /api/orders/:id/shipping

```
功能：Update shipping address (before shipped)

Request:
{
  "name": "张三",
  "phone": "13800138000",
  "address": "北京市朝阳区xxx街道xxx号"
}

Response:
{
  "success": true
}
```

### 6.4 Python CLIP Service

#### POST /api/embedding

```
功能：Generate embedding for single image

Request:
{
  "imageUrl": "https://..."
}

Response:
{
  "embedding": [0.023, -0.156, ...],
  "dimensions": 512
}
```

#### POST /api/embedding/batch

```
功能：Generate embeddings for multiple images

Request:
{
  "images": [
    { "id": "1", "imageUrl": "https://..." },
    { "id": "2", "imageUrl": "https://..." }
  ]
}

Response:
{
  "results": [
    { "id": "1", "embedding": [...] },
    { "id": "2", "embedding": [...] }
  ]
}
```

---

## 七、Event Worker (Pub/Sub Consumer)

### 7.1 Worker Service

```python
# app/main.py

from fastapi import FastAPI, Request
from app.services.activity_processor import process_activity_batch

app = FastAPI()

@app.post("/process")
async def process_pubsub_message(request: Request):
    """
    Called by Pub/Sub push subscription.
    """
    envelope = await request.json()

    # Decode Pub/Sub message
    import base64
    import json

    message_data = envelope.get("message", {}).get("data", "")
    events = json.loads(base64.b64decode(message_data))

    # Process events
    await process_activity_batch(events)

    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### 7.2 Activity Processor

```python
# app/services/activity_processor.py

from sqlalchemy.orm import Session
from app.services.embedding_updater import update_user_embedding
from app.database import get_db

# Signal weights
SIGNAL_WEIGHTS = {
    'purchase': 1.0,
    'save': 0.5,
    'share': 0.4,
    'click': 0.2,
    'view': 0.1,  # Base, adjusted by dwell time
    'impression': 0,
    'hide': -0.5,
    'unsave': -0.3,
    'style_select': 0,  # Handled separately
}

async def process_activity_batch(events: list[dict]):
    """
    Process a batch of activity events.
    """
    db = get_db()

    # Group by visitor
    by_visitor = {}
    for event in events:
        vid = event.get('visitorId')
        if vid not in by_visitor:
            by_visitor[vid] = []
        by_visitor[vid].append(event)

    # Process each visitor's events
    for visitor_id, visitor_events in by_visitor.items():
        await process_visitor_events(db, visitor_id, visitor_events)

    db.close()


async def process_visitor_events(db: Session, visitor_id: str, events: list[dict]):
    """
    Process all events for a single visitor.
    Update their embedding accordingly.
    """
    from app.models import UserPreference, Painting, Activity

    # Get current user embedding
    user = db.query(UserPreference).filter(
        UserPreference.visitor_id == visitor_id
    ).first()

    if not user or not user.embedding:
        # New user with no embedding - skip or use default
        return

    current_embedding = list(user.embedding)
    updated = False

    for event in events:
        # Save to activity log
        activity = Activity(
            visitor_id=visitor_id,
            session_id=event.get('sessionId'),
            event=event.get('event'),
            painting_id=event.get('paintingId'),
            position=event.get('position'),
            source=event.get('source'),
            metadata=event.get('metadata'),
            processed=True
        )
        db.add(activity)

        # Get signal weight
        weight = get_signal_weight(event)

        # Update embedding if we have a painting and non-zero weight
        if weight != 0 and event.get('paintingId'):
            painting = db.query(Painting).filter(
                Painting.id == event['paintingId']
            ).first()

            if painting:
                current_embedding = update_user_embedding(
                    current_embedding,
                    list(painting.embedding),
                    weight
                )
                updated = True

    # Save updated embedding
    if updated:
        user.embedding = current_embedding
        user.interaction_count += len(events)
        user.updated_at = datetime.utcnow()

    db.commit()


def get_signal_weight(event: dict) -> float:
    """
    Calculate signal weight for an event.
    """
    event_type = event.get('event')
    base_weight = SIGNAL_WEIGHTS.get(event_type, 0)

    # Adjust view weight by dwell time
    if event_type == 'view':
        metadata = event.get('metadata', {})
        dwell_ms = metadata.get('dwellTimeMs', 0)

        if dwell_ms > 5000:
            return 0.3
        elif dwell_ms > 3000:
            return 0.2
        elif dwell_ms > 1000:
            return 0.1
        else:
            return 0

    return base_weight
```

### 7.3 Embedding Updater

```python
# app/services/embedding_updater.py

import numpy as np

def update_user_embedding(
    user_embedding: list[float],
    painting_embedding: list[float],
    signal_weight: float,
    learning_rate: float = 0.1
) -> list[float]:
    """
    Update user embedding based on interaction.

    Positive weight → Move toward painting
    Negative weight → Move away from painting
    """
    user_vec = np.array(user_embedding)
    painting_vec = np.array(painting_embedding)

    # Direction from user to painting
    direction = painting_vec - user_vec

    # Update: move in direction scaled by weight and learning rate
    new_embedding = user_vec + learning_rate * signal_weight * direction

    # Normalize to unit vector
    norm = np.linalg.norm(new_embedding)
    if norm > 0:
        new_embedding = new_embedding / norm

    return new_embedding.tolist()


def combine_embeddings(
    embeddings: list[tuple[list[float], float]]
) -> list[float]:
    """
    Combine multiple embeddings with weights.

    Args:
        embeddings: List of (embedding, weight) tuples

    Returns:
        Combined normalized embedding
    """
    result = np.zeros(512)
    total_weight = 0

    for emb, weight in embeddings:
        result += np.array(emb) * weight
        total_weight += weight

    if total_weight > 0:
        result /= total_weight

    # Normalize
    norm = np.linalg.norm(result)
    if norm > 0:
        result = result / norm

    return result.tolist()
```

---

## 八、Payment Workflow (Stripe)

### 8.1 Payment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  User clicks "Buy"                                              │
│        ↓                                                        │
│  POST /api/checkout                                             │
│  - Create order (status: pending)                               │
│  - Create Stripe Checkout session                               │
│  - Return checkout URL                                          │
│        ↓                                                        │
│  Redirect to Stripe Checkout                                    │
│        ↓                                                        │
│  User pays on Stripe                                            │
│        ↓                                                        │
│  Stripe sends webhook (checkout.session.completed)              │
│        ↓                                                        │
│  POST /api/webhooks/stripe                                      │
│  - Verify signature                                             │
│  - Update order (status: paid)                                  │
│  - Log purchase activity                                        │
│  - Update user embedding (+1.0 weight)                          │
│        ↓                                                        │
│  Redirect to success page                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Pricing Configuration

```typescript
// lib/pricing.ts

export const PRICING = {
  sizes: {
    '40x50': { name: '40×50cm', basePrice: 19900 },   // ¥199
    '50x60': { name: '50×60cm', basePrice: 24900 },   // ¥249
    '60x80': { name: '60×80cm', basePrice: 29900 },   // ¥299
    '80x100': { name: '80×100cm', basePrice: 39900 }, // ¥399
  },
  materials: {
    'paper': { name: '高清打印纸', multiplier: 1.0 },
    'canvas': { name: '油画布', multiplier: 1.3 },
    'textured': { name: '肌理画布', multiplier: 1.6 },
  },
  frames: {
    'none': { name: '无框', price: 0 },
    'black': { name: '黑色细框', price: 5000 },      // +¥50
    'white': { name: '白色细框', price: 5000 },      // +¥50
    'wood': { name: '原木框', price: 8000 },         // +¥80
    'gold': { name: '金色框', price: 10000 },        // +¥100
  }
}

export function calculatePrice(
  size: string,
  material: string,
  frame: string
): number {
  const basePrice = PRICING.sizes[size]?.basePrice || 29900
  const materialMultiplier = PRICING.materials[material]?.multiplier || 1.0
  const framePrice = PRICING.frames[frame]?.price || 0

  return Math.round(basePrice * materialMultiplier) + framePrice
}
```

### 8.3 Checkout API Implementation

```typescript
// app/api/checkout/route.ts

import Stripe from 'stripe'
import { db } from '@/lib/db'
import { calculatePrice, PRICING } from '@/lib/pricing'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  const { paintingId, size, material, frame } = await req.json()
  const visitorId = req.headers.get('x-visitor-id')

  // Get painting details
  const painting = await db.painting.findUnique({
    where: { id: paintingId }
  })

  if (!painting) {
    return Response.json({ error: 'Painting not found' }, { status: 404 })
  }

  // Calculate price
  const amount = calculatePrice(size, material, frame)

  // Create order
  const orderId = `order_${crypto.randomUUID().slice(0, 8)}`
  const order = await db.order.create({
    data: {
      id: orderId,
      visitorId,
      paintingId,
      size,
      material,
      frame,
      amount,
      currency: 'cny',
      status: 'pending',
    }
  })

  // Create Stripe Checkout session
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card', 'alipay', 'wechat_pay'],
    line_items: [{
      price_data: {
        currency: 'cny',
        product_data: {
          name: `《${painting.title}》`,
          description: `${PRICING.sizes[size].name} ${PRICING.materials[material].name}`,
          images: [painting.imageUrl],
        },
        unit_amount: amount,
      },
      quantity: 1,
    }],
    mode: 'payment',
    success_url: `${process.env.NEXT_PUBLIC_URL}/order/${orderId}?success=true`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/painting/${paintingId}`,
    metadata: {
      orderId,
      visitorId,
      paintingId,
    },
    // Collect shipping address
    shipping_address_collection: {
      allowed_countries: ['CN'],
    },
    // Chinese payment methods require CNY
    payment_method_options: {
      wechat_pay: { client: 'web' },
    },
  })

  // Update order with session ID
  await db.order.update({
    where: { id: orderId },
    data: { stripeSessionId: session.id }
  })

  return Response.json({
    checkoutUrl: session.url,
    sessionId: session.id,
    orderId,
  })
}
```

### 8.4 Webhook Handler

```typescript
// app/api/webhooks/stripe/route.ts

import Stripe from 'stripe'
import { headers } from 'next/headers'
import { db } from '@/lib/db'
import { publishToPublub } from '@/lib/pubsub'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  const body = await req.text()
  const signature = headers().get('stripe-signature')!

  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    )
  } catch (err) {
    console.error('Webhook signature verification failed')
    return Response.json({ error: 'Invalid signature' }, { status: 400 })
  }

  // Handle the event
  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session

      const orderId = session.metadata?.orderId
      const visitorId = session.metadata?.visitorId
      const paintingId = session.metadata?.paintingId

      // Update order status
      await db.order.update({
        where: { id: orderId },
        data: {
          status: 'paid',
          paidAt: new Date(),
          stripePaymentIntent: session.payment_intent as string,
          // Shipping info from Stripe
          shippingName: session.shipping_details?.name,
          shippingPhone: session.customer_details?.phone,
          shippingAddress: JSON.stringify(session.shipping_details?.address),
        }
      })

      // Log purchase activity (strongest positive signal)
      await publishToPubsub('artwall-activities', {
        visitorId,
        event: 'purchase',
        paintingId,
        metadata: {
          orderId,
          amount: session.amount_total,
        }
      })

      break
    }

    case 'charge.refunded': {
      const charge = event.data.object as Stripe.Charge
      const paymentIntent = charge.payment_intent as string

      await db.order.updateMany({
        where: { stripePaymentIntent: paymentIntent },
        data: { status: 'refunded' }
      })

      break
    }
  }

  return Response.json({ received: true })
}
```

### 8.5 Order Status Flow

```
pending ──────────────────────────────────────────────────┐
    │                                                      │
    │ (payment successful)                          (30min timeout)
    ▼                                                      ▼
  paid ─────────────────────────────────────────────── expired
    │
    │ (start production)
    ▼
processing
    │
    │ (ship order)
    ▼
 shipped
    │
    │ (delivery confirmed)
    ▼
delivered
    │
    │ (after 7 days, auto-complete)
    ▼
completed

    (at any time after paid)
         │
         ▼
     refunded
```

### 8.6 Admin Order Management

```typescript
// Admin APIs for order management

// Update order status (for fulfillment)
// POST /api/admin/orders/:id/status
{
  "status": "shipped",
  "trackingNumber": "SF123456789"
}

// Get orders for fulfillment
// GET /api/admin/orders?status=paid
{
  "orders": [
    {
      "id": "order_xxx",
      "painting": {...},
      "size": "60x80",
      "shipping": {...},
      "createdAt": "..."
    }
  ]
}
```

---

## 九、Frontend Activity Tracking

### 9.1 Activity Tracker

```typescript
// lib/activity-tracker.ts

interface ActivityEvent {
  event: string
  paintingId?: string
  position?: number
  source?: string
  metadata?: Record<string, any>
}

class ActivityTracker {
  private queue: ActivityEvent[] = []
  private flushInterval = 2000  // 2 seconds
  private visitorId: string
  private sessionId: string

  constructor() {
    this.visitorId = this.getOrCreateVisitorId()
    this.sessionId = this.createSessionId()

    // Periodic flush
    setInterval(() => this.flush(), this.flushInterval)

    // Flush on page hide
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.flush()
      }
    })

    // Track session start
    this.track({ event: 'session_start' })
  }

  track(event: ActivityEvent) {
    this.queue.push({
      ...event,
      timestamp: Date.now()
    })
  }

  private async flush() {
    if (this.queue.length === 0) return

    const events = this.queue.map(e => ({
      ...e,
      visitorId: this.visitorId,
      sessionId: this.sessionId
    }))

    this.queue = []

    try {
      await fetch('/api/activity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events }),
        keepalive: true
      })
    } catch (e) {
      // Re-queue on failure
      this.queue.unshift(...events)
    }
  }

  private getOrCreateVisitorId(): string {
    let id = localStorage.getItem('artwall_visitor_id')
    if (!id) {
      id = 'v_' + crypto.randomUUID()
      localStorage.setItem('artwall_visitor_id', id)
    }
    return id
  }

  private createSessionId(): string {
    return 's_' + crypto.randomUUID()
  }
}

export const tracker = new ActivityTracker()
```

### 9.2 Usage in Components

```typescript
// components/PaintingCard.tsx

import { useRef, useEffect } from 'react'
import { tracker } from '@/lib/activity-tracker'
import { useInView } from 'react-intersection-observer'

interface Props {
  painting: Painting
  position: number
}

export function PaintingCard({ painting, position }: Props) {
  const viewStartTime = useRef<number>(0)
  const { ref, inView } = useInView({ threshold: 0.5 })

  // Track impression and view duration
  useEffect(() => {
    if (inView) {
      // Track impression
      tracker.track({
        event: 'impression',
        paintingId: painting.id,
        position,
        source: 'feed'
      })

      viewStartTime.current = Date.now()
    } else if (viewStartTime.current > 0) {
      // Track view duration when leaving viewport
      const dwellTimeMs = Date.now() - viewStartTime.current

      if (dwellTimeMs > 1000) {
        tracker.track({
          event: 'view',
          paintingId: painting.id,
          position,
          source: 'feed',
          metadata: { dwellTimeMs }
        })
      }

      viewStartTime.current = 0
    }
  }, [inView, painting.id, position])

  const handleClick = () => {
    tracker.track({
      event: 'click',
      paintingId: painting.id,
      position,
      source: 'feed'
    })
  }

  const handleSave = (e: React.MouseEvent) => {
    e.stopPropagation()
    tracker.track({
      event: 'save',
      paintingId: painting.id
    })
    // ... save logic
  }

  return (
    <div ref={ref} onClick={handleClick}>
      <img src={painting.imageUrl} alt={painting.title} />
      <button onClick={handleSave}>Save</button>
    </div>
  )
}
```

---

## 十、Static Configuration

### 10.1 Home Styles (Pre-computed)

```typescript
// packages/config/styles.ts

export interface HomeStyle {
  code: string
  name: string
  nameEn: string
  imageUrl: string
  embedding: number[]  // 512 dimensions, pre-computed
}

export const HOME_STYLES: HomeStyle[] = [
  {
    code: 'modern',
    name: '现代简约',
    nameEn: 'Modern Minimalist',
    imageUrl: '/images/styles/modern.jpg',
    embedding: [0.023, -0.156, 0.089, /* ... 512 values */]
  },
  {
    code: 'nordic',
    name: '北欧',
    nameEn: 'Nordic',
    imageUrl: '/images/styles/nordic.jpg',
    embedding: [0.045, -0.078, 0.112, /* ... 512 values */]
  },
  // ... 6 more styles
]

export function getStyleEmbedding(codes: string[]): number[] {
  const selectedStyles = HOME_STYLES.filter(s => codes.includes(s.code))

  if (selectedStyles.length === 0) {
    throw new Error('No valid styles selected')
  }

  // Average embeddings
  const result = new Array(512).fill(0)

  for (const style of selectedStyles) {
    for (let i = 0; i < 512; i++) {
      result[i] += style.embedding[i] / selectedStyles.length
    }
  }

  // Normalize
  const norm = Math.sqrt(result.reduce((sum, v) => sum + v * v, 0))
  return result.map(v => v / norm)
}
```

### 10.2 Generate Embeddings Script

```python
# scripts/generate-style-embeddings.py

"""
Run this locally to generate embeddings for style images.
Copy output to packages/config/styles.ts
"""

import json
from app.services.embedding_service import embedding_service

STYLES = [
    {"code": "modern", "image": "styles/modern.jpg"},
    {"code": "nordic", "image": "styles/nordic.jpg"},
    {"code": "japanese", "image": "styles/japanese.jpg"},
    {"code": "chinese", "image": "styles/chinese.jpg"},
    {"code": "french", "image": "styles/french.jpg"},
    {"code": "american", "image": "styles/american.jpg"},
    {"code": "industrial", "image": "styles/industrial.jpg"},
    {"code": "cream", "image": "styles/cream.jpg"},
]

def main():
    results = {}

    for style in STYLES:
        print(f"Processing {style['code']}...")
        embedding = embedding_service.get_embedding_from_file(style['image'])
        results[style['code']] = embedding

    # Output as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
```

---

## 十一、Cloud Storage

### 11.1 Bucket Structure

```
gs://artwall-images/
├── paintings/              # Painting thumbnails
│   ├── {painting_id}.jpg
│   └── ...
├── paintings-hd/           # High-res versions
│   └── ...
├── user-rooms/             # User uploaded photos
│   ├── {visitor_id}/
│   │   └── {image_id}.jpg
│   └── ...
└── rendered/               # Rendered previews (if implemented)
    └── ...
```

### 11.2 Upload Helper

```typescript
// lib/storage.ts

import { Storage } from '@google-cloud/storage'

const storage = new Storage()
const bucket = storage.bucket(process.env.GCS_BUCKET!)

export async function uploadImage(
  buffer: Buffer,
  path: string
): Promise<string> {
  const blob = bucket.file(path)

  await blob.save(buffer, {
    contentType: 'image/jpeg',
    metadata: {
      cacheControl: 'public, max-age=31536000'
    }
  })

  return `https://storage.googleapis.com/${bucket.name}/${path}`
}
```

---

## 十二、API Summary

### User APIs (Next.js)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/activity | Log user activities |
| GET | /api/feed | Get personalized feed |
| POST | /api/onboarding/style | Set initial style preference |
| GET | /api/paintings/:id | Get painting details |
| GET | /api/saved | Get saved paintings |
| POST | /api/upload | Upload room photo |

### Payment APIs (Next.js)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/checkout | Create Stripe Checkout session |
| POST | /api/webhooks/stripe | Handle Stripe webhooks |
| GET | /api/orders | Get user's order history |
| GET | /api/orders/:id | Get order details |
| POST | /api/orders/:id/shipping | Update shipping address |

### Admin APIs (Next.js)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/admin/paintings/batch | Batch upload paintings |
| GET | /api/admin/paintings/batch/:jobId | Check batch status |
| POST | /api/admin/paintings | Single painting upload |
| GET | /api/admin/orders | Get orders for fulfillment |
| POST | /api/admin/orders/:id/status | Update order status |

### Python Services

| Method | Endpoint | Service | Description |
|--------|----------|---------|-------------|
| POST | /api/embedding | CLIP | Single image embedding |
| POST | /api/embedding/batch | CLIP | Batch embeddings |
| POST | /process | Worker | Pub/Sub push endpoint |

---

## 十三、GCP Resources

| Resource | Name | Purpose |
|----------|------|---------|
| Project | artwall | GCP project |
| Cloud Run | artwall-web | Next.js app |
| Cloud Run | artwall-clip | CLIP service |
| Cloud Run | artwall-worker | Event worker |
| Cloud SQL | artwall-db | PostgreSQL + pgvector |
| Cloud Storage | artwall-images | Image storage |
| Pub/Sub Topic | artwall-activities | Activity events |
| Pub/Sub Sub | artwall-activities-sub | Push to worker |

---

## 十四、Development Plan

### Phase 1: Infrastructure
- [ ] Create GCP project
- [ ] Setup Cloud SQL (PostgreSQL + pgvector)
- [ ] Create Cloud Storage bucket
- [ ] Setup Pub/Sub topic and subscription
- [ ] Configure Cloud Run services
- [ ] Setup Stripe account and API keys

### Phase 2: Python Services
- [ ] CLIP embedding service
- [ ] Event worker service
- [ ] Deploy to Cloud Run

### Phase 3: Next.js App
- [ ] Project setup with Prisma
- [ ] Activity tracking system
- [ ] Feed API with vector search
- [ ] Onboarding flow
- [ ] Admin batch upload

### Phase 4: Payment
- [ ] Stripe Checkout integration
- [ ] Webhook handler
- [ ] Order management APIs
- [ ] Order status pages
- [ ] Admin order fulfillment UI

### Phase 5: Data
- [ ] Pre-compute style embeddings
- [ ] Crawl paintings from WikiArt/Met
- [ ] Batch import paintings

### Phase 6: Frontend
- [ ] Landing page
- [ ] Style selection (onboarding)
- [ ] Infinite feed
- [ ] Painting detail
- [ ] Save functionality
- [ ] Order history page
- [ ] Checkout flow

---

*Document Version: v5.0*
*Updated: 2025-12-30*
*Key Changes:
- Event-driven architecture with Pub/Sub
- Continuous recommendation (no final results page)
- Activity-based embedding updates
- Static config for styles (no DB table)
- Stripe payment integration with orders table
- Complete checkout and webhook flow*
