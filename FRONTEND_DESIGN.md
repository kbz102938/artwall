# ArtWall Frontend Design Document

## Overview

ArtWall is a mobile-first art discovery app that uses AI-powered recommendations to help users discover paintings that match their home and personal taste. The app creates personalized recommendations by combining:
- **User's room photo** (20% weight) - Visual context of their living space
- **Style preferences** (30% weight) - Selected home decor styles they like
- **Art interactions** (50% weight) - Paintings they view, save, and engage with

---

## Core User Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     ONBOARDING FLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Upload Room Photo                                  │
│  ┌─────────────────────────┐                               │
│  │                         │                               │
│  │   [Camera/Gallery]      │  "Take a photo of your        │
│  │                         │   living room or bedroom"     │
│  │   📷                    │                               │
│  │                         │                               │
│  └─────────────────────────┘                               │
│              ↓                                              │
│  Step 2: Select Home Styles (pick 1-3)                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                          │
│  │现代  │ │北欧  │ │日式  │ │中式  │                          │
│  │简约  │ │     │ │侘寂  │ │     │                          │
│  └─────┘ └─────┘ └─────┘ └─────┘                          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                          │
│  │法式  │ │美式  │ │工业  │ │奶油  │                          │
│  │轻奢  │ │     │ │风   │ │混搭  │                          │
│  └─────┘ └─────┘ └─────┘ └─────┘                          │
│              ↓                                              │
│  Step 3: Show Personalized Feed                            │
│  ┌─────────────────────────┐                               │
│  │                         │                               │
│  │   Painting Feed         │  Based on room + styles       │
│  │   (Swipe vertically)    │                               │
│  │                         │                               │
│  └─────────────────────────┘                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack Recommendation

- **Framework**: React Native (iOS + Android) or Next.js (Web)
- **State Management**: Zustand or React Context
- **HTTP Client**: Axios or fetch
- **Image Handling**: React Native Fast Image / Next.js Image
- **Camera**: expo-camera or react-native-camera
- **Image Upload**: Cloud storage (e.g., Cloudinary, S3) for room photos

---

## API Configuration

### Base URLs
```
Discovery API: https://artwall-api-919123660014.us-central1.run.app
CLIP Service:  https://clip-service-919123660014.us-central1.run.app
```

### Required Headers
All requests must include:
```
x-visitor-id: <unique-visitor-id>
Content-Type: application/json
```

Generate visitor ID on first launch: `v_${uuid}`, persist in local storage.

---

## Screen 1: Room Photo Upload

### Purpose
Capture the visual context of user's living space to match paintings that will look good in their environment.

### UI Layout
```
┌─────────────────────────────┐
│         ArtWall             │
├─────────────────────────────┤
│                             │
│  让我们为您的家找到          │
│  最合适的画作                │
│                             │
│  ┌───────────────────────┐  │
│  │                       │  │
│  │                       │  │
│  │    📷                 │  │
│  │    拍摄您的客厅或卧室    │  │
│  │                       │  │
│  │                       │  │
│  └───────────────────────┘  │
│                             │
│  [  拍照  ]  [  从相册选择  ]  │
│                             │
│          [跳过]              │
│                             │
└─────────────────────────────┘
```

### Behavior
1. User taps "拍照" → Open camera
2. User taps "从相册选择" → Open photo gallery
3. After photo selected → Upload to cloud storage → Get URL
4. Call `/api/onboarding/photo` with image URL
5. Navigate to Style Selection

### API Call
```
POST /api/onboarding/photo
Headers: x-visitor-id: v_xxx
Body: { "imageUrl": "https://storage.example.com/room.jpg" }

Response: { "success": true }
```

### Skip Option
- User can skip this step
- Will only use style preferences for initial recommendations

---

## Screen 2: Style Selection

### Purpose
Let user select 1-3 home decor styles they like. These style images will be used to build their preference embedding.

### Available Styles
| Code | Chinese | English | Keywords |
|------|---------|---------|----------|
| `modern` | 现代简约 | Modern Minimalist | 黑白灰, 线条感 |
| `nordic` | 北欧 | Nordic | 白色, 木质, 绿植 |
| `japanese` | 日式/侘寂 | Japanese Wabi-Sabi | 原木, 低饱和, 禅意 |
| `chinese` | 新中式 | New Chinese | 木质, 对称, 东方元素 |
| `french` | 法式/轻奢 | French Luxury | 石膏线, 金色点缀 |
| `american` | 美式 | American | 深色木质, 复古 |
| `industrial` | 工业风 | Industrial | 水泥, 金属, 管道 |
| `cream` | 奶油风/混搭 | Cream/Eclectic | 柔和色调, 舒适 |

### UI Layout
```
┌─────────────────────────────┐
│  ←                          │
├─────────────────────────────┤
│                             │
│  选择您喜欢的家居风格         │
│  (可多选1-3个)               │
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ [image] │ │ [image] │   │
│  │ 现代简约  │ │  北欧    │   │
│  │   ✓     │ │         │   │
│  └─────────┘ └─────────┘   │
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ [image] │ │ [image] │   │
│  │ 日式侘寂  │ │  新中式   │   │
│  │         │ │   ✓     │   │
│  └─────────┘ └─────────┘   │
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ [image] │ │ [image] │   │
│  │ 法式轻奢  │ │  美式    │   │
│  └─────────┘ └─────────┘   │
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ [image] │ │ [image] │   │
│  │  工业风  │ │ 奶油混搭  │   │
│  └─────────┘ └─────────┘   │
│                             │
│  [    开始探索 (2/3)    ]    │
│                             │
└─────────────────────────────┘
```

### Behavior
1. Display grid of style cards with representative images
2. Tap to select/deselect (show checkmark)
3. Allow 1-3 selections
4. "开始探索" button shows count, disabled if 0 selected
5. On submit → Call `/api/onboarding/style`
6. Navigate to Feed

### API Calls

**Get available styles:**
```
GET /api/onboarding/style

Response:
{
  "styles": [
    {
      "code": "modern",
      "name": "现代简约",
      "nameEn": "Modern Minimalist",
      "imageUrl": "/images/styles/modern.jpg",
      "keywords": ["黑白灰", "线条感", "少即是多"]
    },
    ...
  ]
}
```

**Submit selections:**
```
POST /api/onboarding/style
Headers: x-visitor-id: v_xxx
Body: {
  "styleCodes": ["modern", "chinese"],
  "styleImageUrls": [
    "https://example.com/modern-room.jpg",
    "https://example.com/chinese-room.jpg"
  ]
}

Response: { "success": true, "styles": [...] }
```

### Style Images
You need to provide representative images for each style. These should be:
- High-quality interior design photos
- Clearly representing the style
- 1:1 or 4:3 aspect ratio
- Hosted on CDN for fast loading

---

## Screen 3: Painting Feed (Home)

### Purpose
Show personalized painting recommendations in a TikTok-style vertical swipe feed.

### UI Layout
```
┌─────────────────────────────┐
│                             │
│                             │
│                             │
│                             │
│      [Painting Image]       │
│      (Full Screen)          │
│                             │
│                             │
│                             │
│                             │
├─────────────────────────────┤
│ 《山居秋暝》                  │
│ 王维 • 唐代                   │
├─────────────────────────────┤
│   ♡        ↗        ℹ️      │
│  收藏      分享      详情     │
└─────────────────────────────┘
│  🏠       ❤️       👤       │
│  首页     收藏      我的      │
└─────────────────────────────┘
```

### Behavior
- Swipe up → Next painting
- Swipe down → Previous painting
- Double-tap → Zoom image (track `zoom` event)
- Tap ♡ → Save painting (track `save` event)
- Tap ↗ → Share (track `share` event)
- Tap ℹ️ → Open detail modal

### Activity Tracking
Track these events to improve recommendations:

| Event | Trigger | Weight |
|-------|---------|--------|
| `view` | Painting visible >2s | 1.0 |
| `zoom` | Double-tap to zoom | 2.0 |
| `share` | Share button tapped | 3.0 |
| `save` | Heart button tapped | 4.0 |

### API Calls

**Fetch feed:**
```
GET /api/feed?offset=0&limit=10
Headers: x-visitor-id: v_xxx

Response:
{
  "paintings": [
    {
      "id": "met_42260",
      "title": "山居秋暝",
      "artist": "王维",
      "year": 761,
      "imageUrl": "https://...",
      "aspectRatio": "portrait",
      "similarity": 0.95
    }
  ],
  "nextOffset": 10,
  "hasMore": true
}
```

**Track activity:**
```
POST /api/activity
Headers: x-visitor-id: v_xxx
Body:
{
  "events": [
    {
      "event": "view",
      "paintingId": "met_42260",
      "timestamp": 1704067200000,
      "metadata": { "duration": 5000 }
    }
  ]
}
```

---

## Screen 4: Painting Detail

### UI Layout
```
┌─────────────────────────────┐
│  ←                    ♡  ↗  │
├─────────────────────────────┤
│                             │
│                             │
│    [Painting Image]         │
│    (Zoomable/Pannable)      │
│                             │
│                             │
├─────────────────────────────┤
│ 《山居秋暝》                  │
│                             │
│ 艺术家: 王维                  │
│ 年代: 唐代 (761年)            │
│ 风格: 山水画                  │
├─────────────────────────────┤
│ 来源: 大都会艺术博物馆         │
│ 版权: CC0 公共领域             │
│ [查看原作 ↗]                 │
└─────────────────────────────┘
```

### API Call
```
GET /api/paintings/:id
Headers: x-visitor-id: v_xxx

Response:
{
  "painting": {
    "id": "met_42260",
    "title": "山居秋暝",
    "artist": "王维",
    "year": 761,
    "style": "山水画",
    "imageUrl": "https://...",
    "imageHdUrl": "https://.../original.jpg",
    "source": "met",
    "sourceUrl": "https://www.metmuseum.org/...",
    "license": "CC0 1.0",
    "isSaved": false
  }
}
```

---

## Screen 5: Saved/Favorites

### UI Layout
```
┌─────────────────────────────┐
│  我的收藏                    │
├─────────────────────────────┤
│ ┌───────┐ ┌───────┐        │
│ │       │ │       │        │
│ │ img   │ │ img   │        │
│ │       │ │       │        │
│ └───────┘ └───────┘        │
│  标题      标题              │
│                             │
│ ┌───────┐ ┌───────┐        │
│ │       │ │       │        │
│ │ img   │ │ img   │        │
│ │       │ │       │        │
│ └───────┘ └───────┘        │
│  标题      标题              │
└─────────────────────────────┘
```

### API Calls

**Get saved:**
```
GET /api/saved
Headers: x-visitor-id: v_xxx

Response:
{
  "paintings": [
    { "id": "...", "title": "...", "imageUrl": "...", "savedAt": "..." }
  ]
}
```

**Save/Unsave:**
```
POST /api/saved
Headers: x-visitor-id: v_xxx
Body: { "paintingId": "met_42260", "action": "save" }

Response: { "success": true, "isSaved": true }
```

---

## Navigation Structure

```
App
├── Onboarding (first launch only)
│   ├── RoomPhotoScreen
│   └── StyleSelectionScreen
│
└── MainTabs
    ├── FeedTab (Home)
    │   └── PaintingDetail (Modal)
    ├── SavedTab
    │   └── PaintingDetail (Modal)
    └── ProfileTab
```

### First Launch Detection
```typescript
const hasCompletedOnboarding = await AsyncStorage.getItem('onboarding_complete');
if (!hasCompletedOnboarding) {
  // Show onboarding flow
} else {
  // Go to main tabs
}
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

interface HomeStyle {
  code: string;
  name: string;
  nameEn: string;
  imageUrl: string;
  keywords: string[];
}

interface OnboardingState {
  roomPhotoUrl?: string;
  selectedStyles: string[];
  isComplete: boolean;
}

interface ActivityEvent {
  event: 'view' | 'zoom' | 'share' | 'save';
  paintingId: string;
  timestamp: number;
  metadata?: {
    duration?: number;
    source?: string;
  };
}
```

---

## Recommendation Algorithm Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER EMBEDDING                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Room Photo ──→ CLIP ──→ Embedding (20%)                  │
│        +                                                    │
│   Style Images ──→ CLIP ──→ Embedding (30%)                │
│        +                                                    │
│   Art Interactions ──→ Weighted Avg ──→ Embedding (50%)    │
│        ↓                                                    │
│   Combined User Embedding (512-dim vector)                  │
│        ↓                                                    │
│   pgvector similarity search                                │
│        ↓                                                    │
│   Personalized Painting Recommendations                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Image Assets Required

### Style Images (8 images)
Host these on CDN and update `imageUrl` in styles:
- `/images/styles/modern.jpg` - Modern minimalist interior
- `/images/styles/nordic.jpg` - Nordic/Scandinavian interior
- `/images/styles/japanese.jpg` - Japanese wabi-sabi interior
- `/images/styles/chinese.jpg` - New Chinese style interior
- `/images/styles/french.jpg` - French luxury interior
- `/images/styles/american.jpg` - American style interior
- `/images/styles/industrial.jpg` - Industrial loft interior
- `/images/styles/cream.jpg` - Cream/eclectic interior

### Onboarding Assets
- Camera icon/illustration
- Checkmark icon for selection
- Welcome/intro illustrations

---

## Error States

### No Network
```
┌─────────────────────────────┐
│                             │
│         📡                  │
│                             │
│     无法连接网络              │
│     请检查您的网络设置         │
│                             │
│      [ 重试 ]               │
│                             │
└─────────────────────────────┘
```

### Empty Saved
```
┌─────────────────────────────┐
│                             │
│         ♡                   │
│                             │
│     还没有收藏的画作          │
│     去首页探索吧              │
│                             │
│      [ 去探索 ]              │
│                             │
└─────────────────────────────┘
```

---

## Performance Considerations

1. **Image Preloading**: Preload next 3-5 paintings in feed
2. **Skeleton Loading**: Show placeholders while images load
3. **Batch Activity Events**: Send every 2-3 seconds, not per event
4. **Cache Styles**: Cache style images after first load
5. **Offline Queue**: Queue activity events when offline

---

## Testing Checklist

### Onboarding
- [ ] Camera capture works
- [ ] Gallery picker works
- [ ] Skip photo option works
- [ ] Style selection allows 1-3 choices
- [ ] Style images load correctly
- [ ] Onboarding state persists

### Feed
- [ ] Feed loads after onboarding
- [ ] Swipe navigation smooth
- [ ] Images load progressively
- [ ] Activity tracking works
- [ ] Save/unsave updates immediately

### General
- [ ] Visitor ID persists across sessions
- [ ] Offline handling works
- [ ] Deep links work
- [ ] Share functionality works
