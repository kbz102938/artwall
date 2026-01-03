import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const visitorId = request.headers.get("x-visitor-id");
    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    // Get user preference with placement suggestion
    const userPref = await db.userPreference.findUnique({
      where: { visitorId },
      select: {
        roomPhotoUrl: true,
        placementSuggestion: true,
      },
    });

    if (!userPref) {
      return NextResponse.json({
        placement: null,
        roomPhotoUrl: null,
      });
    }

    return NextResponse.json({
      placement: userPref.placementSuggestion,
      roomPhotoUrl: userPref.roomPhotoUrl,
    });
  } catch (error) {
    console.error("Error fetching placement:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
