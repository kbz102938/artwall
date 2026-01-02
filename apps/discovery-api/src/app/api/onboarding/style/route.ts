import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

// GET: Fetch all available home styles
export async function GET() {
  try {
    const styles = await db.$queryRaw<
      { id: number; name: string; name_en: string | null; image_url: string }[]
    >`
      SELECT id, name, name_en, image_url FROM home_styles ORDER BY id
    `;

    return NextResponse.json({
      styles: styles.map((s) => ({
        id: s.id,
        name: s.name,
        nameEn: s.name_en,
        imageUrl: s.image_url,
      })),
    });
  } catch (error) {
    console.error("Error fetching styles:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// POST: Save user's selected styles
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { styleIds } = body as { styleIds: number[] };

    if (!styleIds || !Array.isArray(styleIds) || styleIds.length === 0) {
      return NextResponse.json(
        { error: "No style IDs provided" },
        { status: 400 }
      );
    }

    if (styleIds.length > 3) {
      return NextResponse.json(
        { error: "Maximum 3 styles allowed" },
        { status: 400 }
      );
    }

    const visitorId = request.headers.get("x-visitor-id");
    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    // Validate style IDs exist
    const validStyles = await db.$queryRaw<
      { id: number; name: string; name_en: string | null }[]
    >`
      SELECT id, name, name_en FROM home_styles WHERE id = ANY(${styleIds}::int[])
    `;

    if (validStyles.length === 0) {
      return NextResponse.json(
        { error: "Invalid style IDs" },
        { status: 400 }
      );
    }

    // Ensure user_preference exists
    await db.userPreference.upsert({
      where: { visitorId },
      create: {
        visitorId,
        interactionCount: 0,
      },
      update: {},
    });

    // Delete existing style selections for this user
    await db.$executeRaw`
      DELETE FROM user_style_selections WHERE visitor_id = ${visitorId}
    `;

    // Insert new style selections
    for (const styleId of styleIds) {
      await db.$executeRaw`
        INSERT INTO user_style_selections (visitor_id, style_id, selected_at)
        VALUES (${visitorId}, ${styleId}, NOW())
      `;
    }

    return NextResponse.json({
      success: true,
      styles: validStyles.map((s) => ({
        id: s.id,
        name: s.name,
        nameEn: s.name_en,
      })),
    });
  } catch (error) {
    console.error("Error setting style preference:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
