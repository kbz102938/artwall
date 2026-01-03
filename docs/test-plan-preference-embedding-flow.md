# Test Plan: User Preference Selection & Embedding Update Flow

## Overview

This document outlines the test strategy for validating the user preference selection, navigation signal tracking, and embedding update mechanisms in ArtWall.

---

## System Architecture Summary

### Current Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Onboarding  │ ──► │  2. Navigation  │ ──► │  3. Embedding   │
│  Style Select   │     │  Signals        │     │  Update         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ user_style_     │     │ activities      │     │ user_preferences│
│ selections      │     │ table           │     │ .embedding      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  4. Feed        │
                                                │  Recommendations│
                                                └─────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Style Selection API | `/api/onboarding/style` | User selects up to 3 home styles |
| Activity Tracking API | `/api/activity` | Records view, zoom, save, purchase events |
| Event Worker | `/apps/event-worker` | Background processor for embedding updates |
| Feed API | `/api/feed` | Returns personalized recommendations |

### Activity Weights

| Event Type | Base Weight | Notes |
|------------|-------------|-------|
| `view` | 1.0 | Duration boost: `min(duration/5000, 3.0)` |
| `zoom` | 2.0 | |
| `share` | 3.0 | |
| `save` | 4.0 | |
| `purchase` | 5.0 | |

### Embedding Update Algorithm (EMA)

```python
learning_rate = 0.1
new_embedding = (1 - learning_rate) * current_embedding + learning_rate * weighted_update
# Result is L2 normalized to unit vector
```

---

## Test Phases

### Phase 1: Initial Preference Selection

**Objective:** Verify that style selection correctly initializes user preferences.

| ID | Test Case | Steps | Expected Result |
|----|-----------|-------|-----------------|
| 1.1 | New user style selection | 1. Create new visitor ID<br>2. POST to `/api/onboarding/style` with 2-3 styleIds | - Returns 200 with selected styles<br>- `user_style_selections` has correct records |
| 1.2 | Verify initial state | Query `user_preferences` for visitor | - `embedding` is NULL<br>- `interactionCount` = 0 |
| 1.3 | Style-based feed | GET `/api/feed` with visitor ID | Returns paintings similar to selected styles |
| 1.4 | Duplicate selection | POST same styles again | Should upsert, not create duplicates |
| 1.5 | Invalid style ID | POST with non-existent styleId | Returns 400 error |

### Phase 2: Navigation Signal Tracking

**Objective:** Verify that user interactions are correctly captured and stored.

| ID | Test Case | Steps | Expected Result |
|----|-----------|-------|-----------------|
| 2.1 | View event (short) | POST `/api/activity` with event="view", duration=2000 | Activity saved with weight=1.0 |
| 2.2 | View event (long) | POST `/api/activity` with event="view", duration=15000 | Activity saved with duration boost (capped at 3.0) |
| 2.3 | Zoom event | POST `/api/activity` with event="zoom" | Activity saved with weight=2.0 |
| 2.4 | Save event | POST `/api/activity` with event="save" | Activity saved with weight=4.0 |
| 2.5 | Purchase event | POST `/api/activity` with event="purchase" | Activity saved with weight=5.0 |
| 2.6 | Batch events | POST array of multiple events | All events saved with correct timestamps |
| 2.7 | Missing paintingId | POST activity without paintingId | Should still save (some events are global) |
| 2.8 | Invalid visitor | POST with empty visitorId | Returns 400 error |

### Phase 3: Embedding Update Verification

**Objective:** Verify that the event worker correctly updates user embeddings.

| ID | Test Case | Steps | Expected Result |
|----|-----------|-------|-----------------|
| 3.1 | First interaction | 1. Save 1 painting<br>2. Trigger worker<br>3. Query user embedding | Embedding ≈ painting's embedding * 0.1 |
| 3.2 | Processed flag | Query activities after worker run | `processed = true` for handled activities |
| 3.3 | Interaction count | Query `user_preferences` | `interactionCount` incremented |
| 3.4 | Multiple interactions | Save 3 different paintings, trigger worker | Embedding is weighted average |
| 3.5 | EMA continuity | Add more interactions, trigger worker again | Embedding shifts gradually (90% old + 10% new) |
| 3.6 | Embedding normalization | Check embedding magnitude | Should be unit vector (magnitude ≈ 1.0) |

### Phase 4: Feed Personalization

**Objective:** Verify that recommendations evolve based on learned preferences.

| ID | Test Case | Steps | Expected Result |
|----|-----------|-------|-----------------|
| 4.1 | Initial feed (no history) | GET `/api/feed` for new visitor | Returns recent paintings (no personalization) |
| 4.2 | Style-based feed | After style selection, GET `/api/feed` | Paintings similar to selected styles |
| 4.3 | Learned preference feed | After embedding update, GET `/api/feed` | Uses MAX of style similarity OR learned similarity |
| 4.4 | Preference drift | Consistently save paintings of different style | Feed gradually shifts toward new preference |
| 4.5 | Shown painting exclusion | Note returned paintings, fetch again | Previously shown paintings excluded |

---

## End-to-End Test Scenarios

### Scenario A: Cold Start → Style Selection → Browsing

```
Timeline:
─────────────────────────────────────────────────────────────────►

T0: New visitor arrives
    └── No user_preferences record
    └── Feed returns recent paintings (default)

T1: Selects "Minimalist" and "Japanese" styles
    └── user_style_selections: 2 records created
    └── user_preferences: created with embedding=NULL, interactionCount=0
    └── Feed returns paintings similar to Minimalist OR Japanese

T2: Views 5 paintings, saves 1 (painting P1)
    └── activities: 6 records created (5 view + 1 save)
    └── Activities marked processed=false

T3: Event worker runs
    └── Calculates weighted update from P1 (save weight=4.0)
    └── user_preferences.embedding = 0.1 * normalized(P1.embedding)
    └── interactionCount = 1
    └── activities.processed = true

T4: Fetches feed
    └── Feed uses GREATEST(style_similarity, learned_similarity)
    └── Should prioritize paintings similar to P1
```

**Verification Points:**
- [ ] Feed at T0 shows recent paintings
- [ ] Feed at T1 shows style-matched paintings
- [ ] Embedding at T3 is non-null and points toward P1
- [ ] Feed at T4 reflects learned preference

### Scenario B: Preference Drift Over Time

```
Initial State:
    └── User selected "Abstract" style
    └── Feed shows Abstract paintings

Week 1-2: User consistently saves Impressionist paintings
    └── Each save: activity recorded
    └── Worker updates embedding toward Impressionist

Week 3+: Preference has drifted
    └── Embedding now closer to Impressionist paintings
    └── Feed recommends Impressionist even though "Abstract" was selected
```

**Verification Points:**
- [ ] Initial embedding reflects Abstract preference
- [ ] After multiple Impressionist saves, embedding shifts
- [ ] Cosine similarity to Impressionist paintings increases over time
- [ ] Feed rankings change to favor Impressionist

### Scenario C: Mixed Signals

```
User actions:
    └── Views 10 paintings (weight: 1.0 each)
    └── Zooms on 3 paintings (weight: 2.0 each)
    └── Saves 1 painting (weight: 4.0)

Expected embedding update:
    └── Total weighted contribution:
        - 10 views × 1.0 = 10.0
        - 3 zooms × 2.0 = 6.0
        - 1 save × 4.0 = 4.0
    └── Saved painting has 20% influence (4/20)
    └── Zoomed paintings have 30% influence (6/20)
    └── Viewed paintings have 50% influence (10/20)
```

---

## Test Data Requirements

### Sample Paintings

Need paintings with known embeddings in different style clusters:

| Painting ID | Style Cluster | Embedding Characteristics |
|-------------|---------------|---------------------------|
| P_abstract_1 | Abstract | High values in dimensions 0-100 |
| P_abstract_2 | Abstract | Similar to P_abstract_1 |
| P_impressionist_1 | Impressionist | High values in dimensions 100-200 |
| P_impressionist_2 | Impressionist | Similar to P_impressionist_1 |
| P_minimalist_1 | Minimalist | High values in dimensions 200-300 |

### Sample Styles

| Style ID | Name | Embedding |
|----------|------|-----------|
| S1 | Minimalist | Aligned with minimalist paintings |
| S2 | Japanese | Distinct cluster |
| S3 | Abstract | Aligned with abstract paintings |

---

## API Request Examples

### 1. Style Selection

```bash
# Select styles
curl -X POST http://localhost:3001/api/onboarding/style \
  -H "Content-Type: application/json" \
  -H "x-visitor-id: test-user-001" \
  -d '{
    "styleIds": [1, 3]
  }'
```

### 2. Track Activity

```bash
# Track a save event
curl -X POST http://localhost:3001/api/activity \
  -H "Content-Type: application/json" \
  -d '{
    "visitorId": "test-user-001",
    "sessionId": "session-001",
    "event": "save",
    "paintingId": "painting-uuid-here",
    "position": 5,
    "timestamp": 1704307200000
  }'
```

### 3. Track View with Duration

```bash
# Track a long view (10 seconds)
curl -X POST http://localhost:3001/api/activity \
  -H "Content-Type: application/json" \
  -d '{
    "visitorId": "test-user-001",
    "sessionId": "session-001",
    "event": "view",
    "paintingId": "painting-uuid-here",
    "metadata": {
      "duration": 10000
    }
  }'
```

### 4. Trigger Worker (Manual)

```bash
# Trigger embedding update
curl -X POST http://localhost:8080/process
```

### 5. Fetch Feed

```bash
# Get personalized feed
curl http://localhost:3001/api/feed?offset=0&limit=10 \
  -H "x-visitor-id: test-user-001"
```

---

## Database Verification Queries

### Check User State

```sql
-- User preferences and embedding
SELECT
  "visitorId",
  "interactionCount",
  embedding IS NOT NULL as has_embedding,
  CASE WHEN embedding IS NOT NULL
    THEN sqrt(embedding <-> '[0,0,0,...512 zeros...]'::vector)
  END as embedding_magnitude
FROM user_preferences
WHERE "visitorId" = 'test-user-001';

-- Selected styles
SELECT s.name, s.name_en, sel."selectedAt"
FROM user_style_selections sel
JOIN home_styles s ON s.id = sel."styleId"
WHERE sel."visitorId" = 'test-user-001';
```

### Check Activities

```sql
-- Recent activities for user
SELECT
  id, event, "paintingId", position,
  metadata->>'duration' as duration,
  processed, "createdAt"
FROM activities
WHERE "visitorId" = 'test-user-001'
ORDER BY "createdAt" DESC
LIMIT 20;

-- Unprocessed activity count
SELECT COUNT(*) as unprocessed
FROM activities
WHERE processed = false;
```

### Check Embedding Similarity

```sql
-- Compare user embedding to paintings
SELECT
  p.id, p.title,
  1 - (p.embedding <=> up.embedding) as similarity
FROM paintings p
CROSS JOIN user_preferences up
WHERE up."visitorId" = 'test-user-001'
  AND p.embedding IS NOT NULL
  AND up.embedding IS NOT NULL
ORDER BY similarity DESC
LIMIT 10;
```

---

## Test Implementation Options

### Option 1: Python Integration Tests

```
tests/
├── conftest.py                    # Pytest fixtures
├── test_onboarding.py             # Phase 1 tests
├── test_activity_tracking.py      # Phase 2 tests
├── test_embedding_update.py       # Phase 3 tests
├── test_feed_personalization.py   # Phase 4 tests
└── test_e2e_scenarios.py          # Full flow tests
```

**Pros:** Comprehensive, repeatable, CI/CD ready
**Cons:** Requires test database setup

### Option 2: Shell Script for Manual Testing

Single script that runs through all scenarios with curl commands.

**Pros:** Quick to run, no dependencies
**Cons:** Manual verification needed

### Option 3: Playwright E2E Tests

Test through actual UI interactions.

**Pros:** Tests real user experience
**Cons:** Slower, more brittle

---

## Success Criteria

### Phase 1 Pass Criteria
- [ ] Style selection API returns correct styles
- [ ] Database records created correctly
- [ ] Initial embedding is NULL
- [ ] Feed returns style-matched paintings

### Phase 2 Pass Criteria
- [ ] All activity types recorded correctly
- [ ] Timestamps captured accurately
- [ ] Batch processing works
- [ ] Error handling for invalid requests

### Phase 3 Pass Criteria
- [ ] Embedding updates after worker run
- [ ] EMA formula applied correctly
- [ ] Embedding is normalized (unit vector)
- [ ] Interaction count increments

### Phase 4 Pass Criteria
- [ ] Feed reflects style preferences
- [ ] Feed adapts to learned preferences
- [ ] Shown paintings excluded from feed
- [ ] Preference drift observable over time

---

## Future Considerations

### Negative Signals

Currently not implemented. Consider adding:
- `dislike` event with negative weight
- `skip` event (scrolled past quickly)
- Embedding subtraction for negative signals

### A/B Testing

- Compare recommendation quality with/without learned embeddings
- Test different learning rates (0.05 vs 0.1 vs 0.2)
- Test different activity weights

### Performance Testing

- Load test activity endpoint (high volume)
- Test worker performance with large activity backlog
- Test feed query performance with many users

---

## Appendix: Embedding Dimensions

- **Model:** CLIP ViT-B/32
- **Dimensions:** 512
- **Normalization:** L2 (unit vectors)
- **Storage:** PostgreSQL pgvector

## Appendix: Related Files

| File | Purpose |
|------|---------|
| `/apps/discovery-api/src/app/api/onboarding/style/route.ts` | Style selection endpoint |
| `/apps/discovery-api/src/app/api/activity/route.ts` | Activity tracking endpoint |
| `/apps/discovery-api/src/app/api/feed/route.ts` | Feed with recommendations |
| `/apps/event-worker/app/services/embedding_updater.py` | Embedding update logic |
| `/apps/event-worker/app/config.py` | Activity weights config |
| `/apps/discovery-api/prisma/schema.prisma` | Database schema |
