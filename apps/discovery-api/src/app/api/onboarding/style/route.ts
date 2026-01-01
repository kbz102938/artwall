import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getStylesByCodes, getStyleEmbedding } from "@/lib/styles";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { styleCodes } = body as { styleCodes: string[] };

    if (!styleCodes || !Array.isArray(styleCodes) || styleCodes.length === 0) {
      return NextResponse.json(
        { error: "No style codes provided" },
        { status: 400 }
      );
    }

    // Validate style codes
    const validStyles = getStylesByCodes(styleCodes);
    if (validStyles.length === 0) {
      return NextResponse.json(
        { error: "Invalid style codes" },
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

    // Get embedding for selected styles
    const embedding = getStyleEmbedding(styleCodes);

    // Create or update user preference
    // Note: We can't directly insert embedding with Prisma due to Unsupported type
    // For now, just store the style codes
    await db.userPreference.upsert({
      where: { visitorId },
      create: {
        visitorId,
        lastStyleCodes: styleCodes,
        interactionCount: 0,
      },
      update: {
        lastStyleCodes: styleCodes,
        updatedAt: new Date(),
      },
    });

    // TODO: Update embedding using raw SQL when we have the actual embeddings
    // await db.$executeRaw`
    //   UPDATE user_preferences
    //   SET embedding = ${embedding}::vector
    //   WHERE visitor_id = ${visitorId}
    // `;

    return NextResponse.json({
      success: true,
      styles: validStyles.map((s) => ({
        code: s.code,
        name: s.name,
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
