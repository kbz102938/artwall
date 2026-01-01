# ArtWall Frontend Design Document

## Overview

ArtWall is a mobile-first art discovery app that uses AI-powered recommendations to help users discover paintings they'll love. The app features a TikTok-style vertical swipe feed of paintings, personalized based on user interactions.

## Tech Stack Recommendation

- **Framework**: React Native (iOS + Android) or Next.js (Web)
- **State Management**: Zustand or React Context
- **HTTP Client**: Axios or fetch
- **Image Handling**: React Native Fast Image / Next.js Image
- **Gestures**: React Native Gesture Handler (mobile)

---

## API Configuration

### Base URL
```
Production: https://artwall-api-919123660014.us-central1.run.app
```

### Required Headers
All requests must include:
```
x-visitor-id: <unique-visitor-id>
Content-Type: application/json
```

The `visitor-id` should be:
- Generated on first app launch: `v_${uuid}`
- Persisted in local storage/AsyncStorage
- Sent with every API request

---

## API Endpoints

### 1. GET /api/feed
Fetch personalized painting feed.

**Request:**
```
GET /api/feed?offset=0&limit=10
Headers:
  x-visitor-id: v_abc123
```

**Response:**
```json
{
  "paintings": [
    {
      "id": "met_42260",
      "title": "Recluse Fisherman, Autumn Trees",
      "titleEn": null,
      "artist": "Sheng Mao",
      "artistEn": null,
      "year": 1349,
      "style": "Chinese Painting",
      "imageUrl": "https://images.metmuseum.org/...",
      "tags": ["landscape", "nature"],
      "aspectRatio": "portrait",
      "similarity": 0.95
    }
  ],
  "nextOffset": 10,
  "hasMore": true
}
```

**Pagination:**
- Use `offset` and `limit` for pagination
- When `hasMore` is false, no more paintings available
- Typical limit: 10-20 paintings per request

---

### 2. GET /api/paintings/:id
Fetch single painting details.

**Request:**
```
GET /api/paintings/met_42260
Headers:
  x-visitor-id: v_abc123
```

**Response:**
```json
{
  "painting": {
    "id": "met_42260",
    "title": "Recluse Fisherman, Autumn Trees",
    "titleEn": null,
    "artist": "Sheng Mao",
    "artistEn": null,
    "year": 1349,
    "style": "Chinese Painting",
    "imageUrl": "https://images.metmuseum.org/...",
    "imageHdUrl": "https://images.metmuseum.org/.../original.jpg",
    "source": "met",
    "sourceUrl": "https://www.metmuseum.org/art/collection/search/42260",
    "license": "CC0 1.0",
    "tags": ["landscape", "nature"],
    "aspectRatio": "portrait",
    "isSaved": false
  }
}
```

---

### 3. POST /api/activity
Track user interactions (for recommendation improvement).

**Request:**
```json
POST /api/activity
Headers:
  x-visitor-id: v_abc123
Body:
{
  "events": [
    {
      "event": "view",
      "paintingId": "met_42260",
      "timestamp": 1704067200000,
      "metadata": {
        "duration": 5000,
        "source": "feed"
      }
    }
  ]
}
```

**Event Types:**
| Event | Description | Weight |
|-------|-------------|--------|
| `view` | User viewed painting (>2s) | 1.0 |
| `zoom` | User zoomed/expanded image | 2.0 |
| `share` | User shared painting | 3.0 |
| `save` | User saved to favorites | 4.0 |
| `purchase` | User purchased print | 5.0 |

**Response:**
```json
{
  "received": true,
  "count": 1
}
```

**Best Practices:**
- Batch events and send every 2-3 seconds
- Send on app background/close
- Include duration for view events

---

### 4. GET /api/saved
Fetch user's saved paintings.

**Request:**
```
GET /api/saved
Headers:
  x-visitor-id: v_abc123
```

**Response:**
```json
{
  "paintings": [
    {
      "id": "met_42260",
      "title": "Recluse Fisherman, Autumn Trees",
      "artist": "Sheng Mao",
      "imageUrl": "https://...",
      "savedAt": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### 5. POST /api/saved
Save or unsave a painting.

**Request:**
```json
POST /api/saved
Headers:
  x-visitor-id: v_abc123
Body:
{
  "paintingId": "met_42260",
  "action": "save"  // or "unsave"
}
```

**Response:**
```json
{
  "success": true,
  "isSaved": true
}
```

---

## Screens & Components

### 1. Feed Screen (Home)

**Layout:**
- Full-screen vertical swipe feed (like TikTok/Instagram Reels)
- One painting per screen
- Swipe up = next painting
- Swipe down = previous painting

**Components:**
```
┌─────────────────────────┐
│                         │
│                         │
│      [Painting Image]   │
│      (Full Screen)      │
│                         │
│                         │
├─────────────────────────┤
│ Title                   │
│ Artist • Year           │
├─────────────────────────┤
│ [♡ Save] [↗ Share] [ℹ]  │
└─────────────────────────┘
```

**Behavior:**
- Preload next 3-5 images for smooth scrolling
- Track `view` event when painting visible for >2 seconds
- Double-tap to zoom (track `zoom` event)
- Tap heart to save (track `save` event)

**State:**
```typescript
interface FeedState {
  paintings: Painting[];
  currentIndex: number;
  isLoading: boolean;
  hasMore: boolean;
  offset: number;
}
```

---

### 2. Painting Detail Screen

**Trigger:** Tap info button or painting title

**Layout:**
```
┌─────────────────────────┐
│ [←]              [♡][↗] │
├─────────────────────────┤
│                         │
│    [Painting Image]     │
│    (Zoomable)           │
│                         │
├─────────────────────────┤
│ Title                   │
│ Artist                  │
│ Year • Style            │
├─────────────────────────┤
│ Source: Metropolitan    │
│ License: CC0            │
│ [View Original ↗]       │
├─────────────────────────┤
│                         │
│ [Order Print - ¥299]    │ (Future)
│                         │
└─────────────────────────┘
```

**Features:**
- Pinch-to-zoom on image
- HD image loading (use `imageHdUrl`)
- Link to source museum
- Share functionality

---

### 3. Saved/Favorites Screen

**Layout:**
```
┌─────────────────────────┐
│ Saved Paintings         │
├─────────────────────────┤
│ ┌─────┐ ┌─────┐ ┌─────┐ │
│ │     │ │     │ │     │ │
│ │ img │ │ img │ │ img │ │
│ │     │ │     │ │     │ │
│ └─────┘ └─────┘ └─────┘ │
│ Title   Title   Title   │
│ ┌─────┐ ┌─────┐ ┌─────┐ │
│ │     │ │     │ │     │ │
│ ...                     │
└─────────────────────────┘
```

**Behavior:**
- Grid layout (2-3 columns)
- Tap to open detail view
- Long-press to unsave
- Pull-to-refresh

---

### 4. Profile/Settings Screen

**Layout:**
```
┌─────────────────────────┐
│ Settings                │
├─────────────────────────┤
│ Saved Paintings    [→]  │
│ Order History      [→]  │ (Future)
├─────────────────────────┤
│ About ArtWall      [→]  │
│ Privacy Policy     [→]  │
│ Terms of Service   [→]  │
├─────────────────────────┤
│ Version 1.0.0           │
└─────────────────────────┘
```

---

## Navigation Structure

```
TabNavigator
├── Feed (Home)
│   └── PaintingDetail (Modal/Stack)
├── Saved
│   └── PaintingDetail (Modal/Stack)
└── Profile
    └── Settings
```

---

## Data Models (TypeScript)

```typescript
interface Painting {
  id: string;
  title: string;
  titleEn?: string;
  artist: string;
  artistEn?: string;
  year?: number;
  style?: string;
  imageUrl: string;
  imageHdUrl?: string;
  source?: string;
  sourceUrl?: string;
  license?: string;
  tags?: string[];
  aspectRatio?: 'portrait' | 'landscape' | 'square';
  similarity?: number;
  isSaved?: boolean;
}

interface ActivityEvent {
  event: 'view' | 'zoom' | 'share' | 'save' | 'purchase';
  paintingId: string;
  timestamp: number;
  metadata?: {
    duration?: number;
    source?: string;
    position?: number;
  };
}

interface FeedResponse {
  paintings: Painting[];
  nextOffset: number | null;
  hasMore: boolean;
}
```

---

## Activity Tracking Implementation

```typescript
class ActivityTracker {
  private queue: ActivityEvent[] = [];
  private visitorId: string;
  private flushInterval = 2000; // 2 seconds

  constructor(visitorId: string) {
    this.visitorId = visitorId;
    setInterval(() => this.flush(), this.flushInterval);
  }

  track(event: Omit<ActivityEvent, 'timestamp'>) {
    this.queue.push({
      ...event,
      timestamp: Date.now(),
    });
  }

  async flush() {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    await fetch('/api/activity', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-visitor-id': this.visitorId,
      },
      body: JSON.stringify({ events }),
    });
  }
}
```

---

## Image Handling

### Aspect Ratios
Paintings come in different aspect ratios:
- `portrait`: Height > Width (most common)
- `landscape`: Width > Height
- `square`: Equal dimensions

### Image Loading Strategy
1. Show low-res placeholder or blur hash
2. Load full `imageUrl` for feed
3. Load `imageHdUrl` only in detail view when zooming

### Recommended Image Component Props
```typescript
{
  source: { uri: painting.imageUrl },
  resizeMode: 'contain',
  style: { width: '100%', height: '100%' },
  // For React Native Fast Image:
  priority: index < 3 ? 'high' : 'normal',
}
```

---

## Offline Support (Optional)

For better UX, consider:
1. Cache last 20 viewed paintings
2. Cache all saved paintings
3. Queue activity events when offline
4. Sync when back online

---

## Color Palette Suggestion

```css
--background: #FAFAFA;
--surface: #FFFFFF;
--primary: #1A1A1A;
--secondary: #666666;
--accent: #E53935;  /* For save/like button */
--border: #EEEEEE;
```

---

## Performance Tips

1. **Virtualized List**: Use FlatList (RN) or virtualized list for feed
2. **Image Preloading**: Preload next 3-5 images
3. **Skeleton Loading**: Show skeleton while images load
4. **Debounce**: Debounce save/unsave actions
5. **Batch Events**: Don't send activity events one by one

---

## Error Handling

```typescript
// API Error Response Format
{
  "error": "Error message here"
}

// Handle common cases:
// - 400: Bad request (missing visitor-id)
// - 404: Painting not found
// - 500: Server error (show retry option)
// - Network error: Show offline state
```

---

## Testing Checklist

- [ ] Feed loads on app open
- [ ] Swipe navigation works smoothly
- [ ] Images load progressively
- [ ] Save/unsave updates UI immediately
- [ ] Activity tracking sends events
- [ ] Saved paintings persist across sessions
- [ ] Offline mode shows cached content
- [ ] Deep links to paintings work
- [ ] Share functionality works
- [ ] Zoom gesture on detail view works

---

## Future Features (Not in MVP)

1. **Onboarding**: Style preference selection
2. **Search**: Text search for paintings
3. **Filters**: Filter by artist, year, style
4. **Print Orders**: E-commerce checkout flow
5. **Social**: Share collections, follow users
6. **AR View**: Preview painting on wall
