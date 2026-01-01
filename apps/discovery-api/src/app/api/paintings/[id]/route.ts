import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

interface PaintingDetail {
  id: string;
  title: string;
  title_en: string | null;
  artist: string;
  artist_en: string | null;
  year: number | null;
  style: string | null;
  image_url: string;
  image_hd_url: string | null;
  source: string | null;
  source_url: string | null;
  license: string | null;
  tags: string[];
  aspect_ratio: string | null;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const visitorId = request.headers.get("x-visitor-id");

    // Get painting details
    const paintings = await db.$queryRaw<PaintingDetail[]>`
      SELECT
        id,
        title,
        title_en,
        artist,
        artist_en,
        year,
        style,
        image_url,
        image_hd_url,
        source,
        source_url,
        license,
        tags,
        aspect_ratio
      FROM paintings
      WHERE id = ${id}
    `;

    if (paintings.length === 0) {
      return NextResponse.json(
        { error: "Painting not found" },
        { status: 404 }
      );
    }

    const painting = paintings[0];

    // Check if user has saved this painting
    let isSaved = false;
    if (visitorId) {
      const saved = await db.savedPainting.findUnique({
        where: {
          visitorId_paintingId: {
            visitorId,
            paintingId: id,
          },
        },
      });
      isSaved = !!saved;
    }

    return NextResponse.json({
      painting: {
        id: painting.id,
        title: painting.title,
        titleEn: painting.title_en,
        artist: painting.artist,
        artistEn: painting.artist_en,
        year: painting.year,
        style: painting.style,
        imageUrl: painting.image_url,
        imageHdUrl: painting.image_hd_url,
        source: painting.source,
        sourceUrl: painting.source_url,
        license: painting.license,
        tags: painting.tags,
        aspectRatio: painting.aspect_ratio,
        isSaved,
      },
    });
  } catch (error) {
    console.error("Error fetching painting:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
