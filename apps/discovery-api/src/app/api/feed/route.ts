import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

interface PaintingResult {
  id: string;
  title: string;
  title_en: string | null;
  artist: string;
  artist_en: string | null;
  year: number | null;
  style: string | null;
  image_url: string;
  tags: string[];
  aspect_ratio: string | null;
  similarity: number;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const offset = parseInt(searchParams.get("offset") || "0");
    const limit = Math.min(parseInt(searchParams.get("limit") || "10"), 50);
    const visitorId = request.headers.get("x-visitor-id");

    let paintings: PaintingResult[];

    if (visitorId) {
      // Get user's selected style IDs
      const userStyles = await db.$queryRaw<{ style_id: number }[]>`
        SELECT style_id FROM user_style_selections WHERE visitor_id = ${visitorId}
      `;

      // Check if user has a learned embedding
      const userEmbedding = await db.$queryRaw<{ embedding: string }[]>`
        SELECT embedding::text FROM user_preferences WHERE visitor_id = ${visitorId}
      `;

      const hasStyles = userStyles.length > 0;
      const hasLearnedEmbedding = userEmbedding.length > 0 && userEmbedding[0].embedding;

      if (hasStyles || hasLearnedEmbedding) {
        // Build MAX similarity query
        // For each painting, compute max similarity across all style embeddings + learned embedding
        const styleIds = userStyles.map((s) => s.style_id);

        paintings = await db.$queryRaw<PaintingResult[]>`
          WITH style_similarities AS (
            SELECT
              p.id as painting_id,
              MAX(1 - (p.embedding <=> hs.embedding)) as max_style_similarity
            FROM paintings p
            CROSS JOIN home_styles hs
            WHERE hs.id = ANY(${styleIds}::int[])
              AND p.embedding IS NOT NULL
            GROUP BY p.id
          ),
          learned_similarity AS (
            SELECT
              p.id as painting_id,
              CASE
                WHEN up.embedding IS NOT NULL
                THEN 1 - (p.embedding <=> up.embedding)
                ELSE 0
              END as learned_similarity
            FROM paintings p
            LEFT JOIN user_preferences up ON up.visitor_id = ${visitorId}
            WHERE p.embedding IS NOT NULL
          )
          SELECT
            p.id,
            p.title,
            p.title_en,
            p.artist,
            p.artist_en,
            p.year,
            p.style,
            p.image_url,
            p.tags,
            p.aspect_ratio,
            GREATEST(
              COALESCE(ss.max_style_similarity, 0),
              COALESCE(ls.learned_similarity, 0)
            ) as similarity
          FROM paintings p
          LEFT JOIN style_similarities ss ON ss.painting_id = p.id
          LEFT JOIN learned_similarity ls ON ls.painting_id = p.id
          WHERE p.embedding IS NOT NULL
            AND p.id NOT IN (
              SELECT painting_id FROM shown_paintings WHERE visitor_id = ${visitorId}
            )
          ORDER BY similarity DESC
          LIMIT ${limit} OFFSET ${offset}
        `;
      } else {
        // No styles and no learned embedding - return recent paintings
        paintings = await db.$queryRaw<PaintingResult[]>`
          SELECT
            p.id,
            p.title,
            p.title_en,
            p.artist,
            p.artist_en,
            p.year,
            p.style,
            p.image_url,
            p.tags,
            p.aspect_ratio,
            1.0 as similarity
          FROM paintings p
          WHERE p.embedding IS NOT NULL
            AND p.id NOT IN (
              SELECT painting_id FROM shown_paintings WHERE visitor_id = ${visitorId}
            )
          ORDER BY p.created_at DESC
          LIMIT ${limit} OFFSET ${offset}
        `;
      }
    } else {
      // No visitor ID - return recent paintings
      paintings = await db.$queryRaw<PaintingResult[]>`
        SELECT
          p.id,
          p.title,
          p.title_en,
          p.artist,
          p.artist_en,
          p.year,
          p.style,
          p.image_url,
          p.tags,
          p.aspect_ratio,
          1.0 as similarity
        FROM paintings p
        WHERE p.embedding IS NOT NULL
        ORDER BY p.created_at DESC
        LIMIT ${limit} OFFSET ${offset}
      `;
    }

    // Record shown paintings (if we have a visitor)
    if (visitorId && paintings.length > 0) {
      // Ensure visitor exists in user_preferences first
      await db.userPreference.upsert({
        where: { visitorId },
        create: {
          visitorId,
          interactionCount: 0,
        },
        update: {},
      });

      const values = paintings.map((p) => `('${visitorId}', '${p.id}', NOW())`).join(", ");
      await db.$executeRawUnsafe(`
        INSERT INTO shown_paintings (visitor_id, painting_id, shown_at)
        VALUES ${values}
        ON CONFLICT (visitor_id, painting_id) DO UPDATE SET shown_at = NOW()
      `);
    }

    return NextResponse.json({
      paintings: paintings.map((p) => ({
        id: p.id,
        title: p.title,
        titleEn: p.title_en,
        artist: p.artist,
        artistEn: p.artist_en,
        year: p.year,
        style: p.style,
        imageUrl: p.image_url,
        tags: p.tags,
        aspectRatio: p.aspect_ratio,
        similarity: Number(p.similarity),
      })),
      nextOffset: paintings.length === limit ? offset + limit : null,
      hasMore: paintings.length === limit,
    });
  } catch (error) {
    console.error("Error fetching feed:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
