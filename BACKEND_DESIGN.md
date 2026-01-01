# ArtWall 后端工程设计

## 一、技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 语言 | TypeScript | 类型安全，前后端统一 |
| 框架 | Node.js + Express / Fastify | 轻量、生态成熟 |
| 数据库 | PostgreSQL | 关系型，支持 JSON 字段 |
| ORM | Prisma | 类型安全，迁移方便 |
| 图片存储 | AWS S3 / Cloudflare R2 | 对象存储 |
| 缓存 | Redis（可选） | MVP 可先不用 |
| 部署 | Vercel / Railway / Fly.io | 快速部署 |

---

## 二、项目结构

```
artwall-backend/
├── src/
│   ├── index.ts                 # 入口文件
│   ├── app.ts                   # Express/Fastify 实例
│   ├── config/
│   │   └── index.ts             # 环境配置
│   ├── routes/
│   │   ├── index.ts             # 路由汇总
│   │   ├── upload.ts            # 图片上传
│   │   ├── recommend.ts         # 画作推荐
│   │   ├── paintings.ts         # 画作 CRUD
│   │   └── render.ts            # 效果渲染
│   ├── controllers/
│   │   ├── uploadController.ts
│   │   ├── recommendController.ts
│   │   ├── paintingsController.ts
│   │   └── renderController.ts
│   ├── services/
│   │   ├── uploadService.ts     # 图片上传逻辑
│   │   ├── recommendService.ts  # 推荐算法
│   │   ├── paintingsService.ts  # 画作查询
│   │   └── renderService.ts     # 渲染逻辑
│   ├── lib/
│   │   ├── prisma.ts            # Prisma 客户端
│   │   ├── s3.ts                # S3 客户端
│   │   └── matcher.ts           # 匹配算法
│   ├── types/
│   │   └── index.ts             # 类型定义
│   └── utils/
│       └── index.ts             # 工具函数
├── prisma/
│   ├── schema.prisma            # 数据库模型
│   ├── migrations/              # 迁移文件
│   └── seed.ts                  # 种子数据
├── scripts/
│   └── import-paintings.ts      # 导入画作脚本
├── .env                         # 环境变量
├── .env.example
├── package.json
├── tsconfig.json
└── README.md
```

---

## 三、数据库设计

### 3.1 Prisma Schema

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// 画作表
model Painting {
  id              String   @id @default(cuid())

  // 基本信息
  title           String                    // 画作名称
  titleEn         String?  @map("title_en") // 英文名
  artist          String                    // 作者
  artistEn        String?  @map("artist_en")
  year            Int?                      // 创作年代
  style           String?                   // 流派

  // 图片
  imageUrl        String   @map("image_url")      // 缩略图
  imageHdUrl      String?  @map("image_hd_url")   // 高清图

  // 来源
  source          String?                   // 来源（WikiArt/Met等）
  sourceUrl       String?  @map("source_url")
  license         String?                   // 版权信息

  // 标签（用于匹配）
  tags            String[]                  // ["cold", "landscape", "western", "minimal"]
  suitableStyles  String[] @map("suitable_styles") // ["modern", "nordic", "japanese"]

  // 规格
  aspectRatio     String?  @map("aspect_ratio")   // "landscape" | "portrait" | "square"
  availableSizes  String[] @map("available_sizes") @default(["40x50", "50x60", "60x80"])

  // 元数据
  createdAt       DateTime @default(now()) @map("created_at")
  updatedAt       DateTime @updatedAt @map("updated_at")

  @@map("paintings")
}

// 家居风格配置表
model HomeStyle {
  id          String   @id @default(cuid())
  code        String   @unique              // "modern", "nordic" 等
  name        String                        // "现代简约"
  nameEn      String?  @map("name_en")      // "Modern Minimalist"
  description String?
  imageUrl    String?  @map("image_url")    // 风格示例图
  keywords    String[]                      // 关键词

  @@map("home_styles")
}

// 偏好测试配置表
model PreferenceTest {
  id          String   @id @default(cuid())
  round       Int                           // 第几轮 (1-5)
  dimension   String                        // "abstract_concrete", "warm_cold" 等
  paintingA   String   @map("painting_a")   // 选项A的画作URL或ID
  paintingB   String   @map("painting_b")   // 选项B的画作URL或ID
  tagA        String   @map("tag_a")        // 选A对应的标签 "concrete"
  tagB        String   @map("tag_b")        // 选B对应的标签 "abstract"

  @@map("preference_tests")
}

// 用户会话（可选，MVP可不用）
model Session {
  id              String   @id @default(cuid())
  roomImageUrl    String?  @map("room_image_url")
  homeStyles      String[] @map("home_styles")
  preferences     Json?                     // [{round: 1, choice: "A"}, ...]
  recommendedIds  String[] @map("recommended_ids")
  createdAt       DateTime @default(now()) @map("created_at")

  @@map("sessions")
}
```

### 3.2 标签系统设计

**画作标签 (tags)：**

| 维度 | 标签值 | 说明 |
|-----|--------|------|
| 具象/抽象 | `concrete`, `abstract` | 具象写实 vs 抽象表现 |
| 色调 | `warm`, `cold`, `neutral` | 暖色 / 冷色 / 中性 |
| 繁简 | `complex`, `minimal` | 繁复 vs 极简 |
| 文化 | `eastern`, `western` | 东方 vs 西方 |
| 主题 | `landscape`, `portrait`, `still_life`, `abstract_art` | 风景/人物/静物/抽象 |

**适合风格 (suitableStyles)：**

| 风格代码 | 说明 |
|---------|------|
| `modern` | 现代简约 |
| `nordic` | 北欧 |
| `japanese` | 日式/侘寂 |
| `chinese` | 新中式 |
| `french` | 法式/轻奢 |
| `american` | 美式 |
| `industrial` | 工业风 |
| `cream` | 奶油风/混搭 |

---

## 四、API 详细设计

### 4.1 图片上传

```
POST /api/upload

功能：上传用户房间照片

Headers:
  Content-Type: multipart/form-data

Body:
  image: File (required)

Response 200:
{
  "success": true,
  "data": {
    "imageUrl": "https://storage.artwall.com/rooms/abc123.jpg"
  }
}

Response 400:
{
  "success": false,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "只支持 JPG/PNG 格式"
  }
}
```

**实现要点：**
- 文件大小限制：10MB
- 格式限制：JPG, PNG
- 使用 presigned URL 或直接上传到 S3
- 返回 CDN 加速后的 URL

---

### 4.2 获取家居风格列表

```
GET /api/styles

功能：获取所有家居风格选项

Response 200:
{
  "success": true,
  "data": {
    "styles": [
      {
        "code": "modern",
        "name": "现代简约",
        "nameEn": "Modern Minimalist",
        "imageUrl": "https://storage.artwall.com/styles/modern.jpg"
      },
      {
        "code": "nordic",
        "name": "北欧",
        "nameEn": "Nordic",
        "imageUrl": "https://storage.artwall.com/styles/nordic.jpg"
      }
      // ... 共8个
    ]
  }
}
```

---

### 4.3 获取偏好测试题目

```
GET /api/preference-tests

功能：获取5轮偏好测试的配置

Response 200:
{
  "success": true,
  "data": {
    "tests": [
      {
        "round": 1,
        "dimension": "abstract_concrete",
        "question": "选择你更喜欢的一幅",
        "optionA": {
          "imageUrl": "https://...",
          "title": "睡莲",
          "artist": "莫奈"
        },
        "optionB": {
          "imageUrl": "https://...",
          "title": "构成第八号",
          "artist": "康定斯基"
        }
      },
      // ... 共5轮
    ]
  }
}
```

---

### 4.4 获取推荐画作

```
POST /api/recommend

功能：根据用户偏好返回匹配的画作

Request:
{
  "homeStyles": ["modern", "nordic"],
  "preferences": [
    {"round": 1, "choice": "A"},
    {"round": 2, "choice": "B"},
    {"round": 3, "choice": "B"},
    {"round": 4, "choice": "A"},
    {"round": 5, "choice": "A"}
  ],
  "page": 1,
  "limit": 20,
  "filter": {                    // 可选筛选
    "theme": "landscape",        // 主题筛选
    "aspectRatio": "landscape"   // 横幅/竖幅
  }
}

Response 200:
{
  "success": true,
  "data": {
    "total": 156,
    "page": 1,
    "limit": 20,
    "paintings": [
      {
        "id": "clx1234567",
        "title": "星月夜",
        "titleEn": "The Starry Night",
        "artist": "文森特·梵高",
        "artistEn": "Vincent van Gogh",
        "year": 1889,
        "style": "后印象派",
        "imageUrl": "https://...",
        "imageHdUrl": "https://...",
        "tags": ["cold", "landscape", "western", "complex"],
        "aspectRatio": "landscape",
        "availableSizes": ["40x50", "50x60", "60x80"],
        "matchScore": 85          // 匹配分数
      },
      // ... more paintings
    ]
  }
}
```

---

### 4.5 获取单个画作详情

```
GET /api/paintings/:id

功能：获取画作详细信息

Response 200:
{
  "success": true,
  "data": {
    "painting": {
      "id": "clx1234567",
      "title": "星月夜",
      "titleEn": "The Starry Night",
      "artist": "文森特·梵高",
      "artistEn": "Vincent van Gogh",
      "year": 1889,
      "style": "后印象派",
      "imageUrl": "https://...",
      "imageHdUrl": "https://...",
      "source": "MoMA",
      "sourceUrl": "https://www.moma.org/...",
      "license": "Public Domain",
      "tags": ["cold", "landscape", "western", "complex"],
      "suitableStyles": ["modern", "nordic", "industrial"],
      "aspectRatio": "landscape",
      "availableSizes": ["40x50", "50x60", "60x80"]
    }
  }
}
```

---

### 4.6 渲染效果图

```
POST /api/render

功能：将画作渲染到用户房间照片中

Request:
{
  "roomImageUrl": "https://storage.artwall.com/rooms/abc123.jpg",
  "paintingImageUrl": "https://storage.artwall.com/paintings/starry-night.jpg",
  "size": "60x80",
  "position": {                  // 可选，指定位置
    "x": 0.5,                    // 水平位置 (0-1)
    "y": 0.4                     // 垂直位置 (0-1)
  }
}

Response 200:
{
  "success": true,
  "data": {
    "renderedImageUrl": "https://storage.artwall.com/rendered/xyz789.jpg"
  }
}
```

**实现方案：**

| 方案 | 说明 | 优缺点 |
|-----|------|--------|
| 方案A | 调用 AI 图像编辑 API（如 Replicate） | 效果好，成本高 |
| 方案B | 使用 OpenCV/Sharp 简单合成 | 成本低，效果一般 |
| 方案C | 前端 Canvas 合成 | 无后端成本，效果可控 |

**MVP 建议：先用方案C（前端合成），后续再优化**

---

## 五、核心业务逻辑

### 5.1 推荐算法

```typescript
// src/lib/matcher.ts

interface Preference {
  round: number
  choice: 'A' | 'B'
}

interface PreferenceWeights {
  concrete: number
  abstract: number
  warm: number
  cold: number
  complex: number
  minimal: number
  eastern: number
  western: number
  landscape: number
  portrait: number
}

// 偏好测试结果转换为标签权重
export function preferenceToWeights(preferences: Preference[]): PreferenceWeights {
  const weights: PreferenceWeights = {
    concrete: 0,
    abstract: 0,
    warm: 0,
    cold: 0,
    complex: 0,
    minimal: 0,
    eastern: 0,
    western: 0,
    landscape: 0,
    portrait: 0,
  }

  preferences.forEach((pref) => {
    switch (pref.round) {
      case 1: // 具象 vs 抽象
        weights[pref.choice === 'A' ? 'concrete' : 'abstract'] = 1
        break
      case 2: // 暖色 vs 冷色
        weights[pref.choice === 'A' ? 'warm' : 'cold'] = 1
        break
      case 3: // 繁复 vs 极简
        weights[pref.choice === 'A' ? 'complex' : 'minimal'] = 1
        break
      case 4: // 东方 vs 西方
        weights[pref.choice === 'A' ? 'eastern' : 'western'] = 1
        break
      case 5: // 风景 vs 人物
        weights[pref.choice === 'A' ? 'landscape' : 'portrait'] = 1
        break
    }
  })

  return weights
}

// 计算画作匹配分数
export function calculateMatchScore(
  painting: { tags: string[]; suitableStyles: string[] },
  userWeights: PreferenceWeights,
  homeStyles: string[]
): number {
  let score = 0

  // 风格匹配 (权重 40%)
  const styleMatch = painting.suitableStyles.some((s) => homeStyles.includes(s))
  if (styleMatch) {
    score += 40
  }

  // 偏好匹配 (权重 60%)
  // 每个匹配的标签加 12 分，最多 5 个标签 = 60 分
  const weightKeys = Object.keys(userWeights) as (keyof PreferenceWeights)[]
  weightKeys.forEach((key) => {
    if (userWeights[key] === 1 && painting.tags.includes(key)) {
      score += 12
    }
  })

  return score
}
```

### 5.2 推荐服务

```typescript
// src/services/recommendService.ts

import { prisma } from '../lib/prisma'
import { preferenceToWeights, calculateMatchScore } from '../lib/matcher'

interface RecommendParams {
  homeStyles: string[]
  preferences: { round: number; choice: 'A' | 'B' }[]
  page: number
  limit: number
  filter?: {
    theme?: string
    aspectRatio?: string
  }
}

export async function getRecommendations(params: RecommendParams) {
  const { homeStyles, preferences, page, limit, filter } = params

  // 1. 转换偏好为权重
  const weights = preferenceToWeights(preferences)

  // 2. 构建查询条件
  const where: any = {}

  // 风格筛选：至少匹配一个家居风格
  where.suitableStyles = {
    hasSome: homeStyles,
  }

  // 可选筛选
  if (filter?.theme) {
    where.tags = {
      has: filter.theme,
    }
  }
  if (filter?.aspectRatio) {
    where.aspectRatio = filter.aspectRatio
  }

  // 3. 查询所有匹配的画作
  const paintings = await prisma.painting.findMany({
    where,
  })

  // 4. 计算匹配分数并排序
  const scoredPaintings = paintings.map((p) => ({
    ...p,
    matchScore: calculateMatchScore(
      { tags: p.tags, suitableStyles: p.suitableStyles },
      weights,
      homeStyles
    ),
  }))

  // 按分数降序排序
  scoredPaintings.sort((a, b) => b.matchScore - a.matchScore)

  // 5. 分页
  const total = scoredPaintings.length
  const start = (page - 1) * limit
  const paginatedPaintings = scoredPaintings.slice(start, start + limit)

  return {
    total,
    page,
    limit,
    paintings: paginatedPaintings,
  }
}
```

---

## 六、环境配置

```env
# .env.example

# Server
PORT=3000
NODE_ENV=development

# Database
DATABASE_URL="postgresql://user:password@localhost:5432/artwall"

# S3 Storage
S3_BUCKET=artwall-storage
S3_REGION=us-east-1
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_ENDPOINT=https://s3.amazonaws.com  # 或 Cloudflare R2 端点

# CDN (可选)
CDN_BASE_URL=https://cdn.artwall.com
```

---

## 七、部署配置

### 7.1 Dockerfile

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY prisma ./prisma
RUN npx prisma generate

COPY dist ./dist

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### 7.2 Railway/Vercel 部署

```json
// vercel.json (如果用 Vercel)
{
  "builds": [
    {
      "src": "src/index.ts",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "src/index.ts"
    }
  ]
}
```

---

## 八、开发计划

### Phase 1: 基础框架
- [ ] 初始化项目结构
- [ ] 配置 TypeScript + ESLint
- [ ] 配置 Prisma + PostgreSQL
- [ ] 实现基础路由框架

### Phase 2: 核心 API
- [ ] GET /api/styles - 家居风格列表
- [ ] GET /api/preference-tests - 偏好测试题目
- [ ] POST /api/recommend - 推荐算法
- [ ] GET /api/paintings/:id - 画作详情

### Phase 3: 图片功能
- [ ] POST /api/upload - 图片上传
- [ ] S3 存储配置
- [ ] POST /api/render - 效果渲染（或前端实现）

### Phase 4: 数据导入
- [ ] 编写画作导入脚本
- [ ] 导入 WikiArt/Met 数据
- [ ] 画作标签打标

---

## 九、API 汇总

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | /api/styles | 获取家居风格列表 |
| GET | /api/preference-tests | 获取偏好测试题目 |
| POST | /api/recommend | 获取推荐画作 |
| GET | /api/paintings/:id | 获取画作详情 |
| POST | /api/upload | 上传房间照片 |
| POST | /api/render | 渲染效果图 |

---

*文档版本: v1.0*
*创建日期: 2025-12-30*
