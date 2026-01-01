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
      // Check if user has an embedding
      const userEmbedding = await db.$queryRaw<{ embedding: string }[]>`
        SELECT embedding::text FROM user_preferences WHERE visitor_id = ${visitorId}
      `;

      if (userEmbedding.length > 0 && userEmbedding[0].embedding) {
        // Vector similarity search - exclude already shown paintings
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
            1 - (p.embedding <=> (SELECT embedding FROM user_preferences WHERE visitor_id = ${visitorId})) as similarity
          FROM paintings p
          WHERE p.embedding IS NOT NULL
            AND p.id NOT IN (
              SELECT painting_id FROM shown_paintings WHERE visitor_id = ${visitorId}
            )
          ORDER BY similarity DESC
          LIMIT ${limit} OFFSET ${offset}
        `;
      } else {
        // No user embedding - return recent paintings, excluding shown
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
          lastStyleCodes: [],
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
