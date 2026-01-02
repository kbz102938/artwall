import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

// GET /api/saved - Get user's saved paintings
export async function GET(request: NextRequest) {
  try {
    const visitorId = request.headers.get("x-visitor-id");

    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    const savedPaintings = await db.savedPainting.findMany({
      where: { visitorId },
      include: {
        painting: {
          select: {
            id: true,
            title: true,
            titleEn: true,
            artist: true,
            artistEn: true,
            year: true,
            style: true,
            imageUrl: true,
            aspectRatio: true,
          },
        },
      },
      orderBy: { savedAt: "desc" },
    });

    return NextResponse.json({
      paintings: savedPaintings.map((sp) => sp.painting),
      total: savedPaintings.length,
    });
  } catch (error) {
    console.error("Error fetching saved paintings:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// POST /api/saved - Save or unsave a painting
export async function POST(request: NextRequest) {
  try {
    const visitorId = request.headers.get("x-visitor-id");

    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { paintingId, action } = body as {
      paintingId: string;
      action: "save" | "unsave";
    };

    if (!paintingId) {
      return NextResponse.json(
        { error: "Painting ID required" },
        { status: 400 }
      );
    }

    // Ensure user preference exists
    await db.userPreference.upsert({
      where: { visitorId },
      create: { visitorId, interactionCount: 0 },
      update: {},
    });

    if (action === "unsave") {
      await db.savedPainting.deleteMany({
        where: { visitorId, paintingId },
      });

      return NextResponse.json({
        success: true,
        action: "unsaved",
        paintingId,
      });
    } else {
      // Default to save
      await db.savedPainting.upsert({
        where: {
          visitorId_paintingId: { visitorId, paintingId },
        },
        create: { visitorId, paintingId },
        update: { savedAt: new Date() },
      });

      return NextResponse.json({
        success: true,
        action: "saved",
        paintingId,
      });
    }
  } catch (error) {
    console.error("Error saving painting:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
