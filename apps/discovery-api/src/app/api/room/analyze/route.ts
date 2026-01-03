import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { db } from "@/lib/db";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const visitorId = request.headers.get("x-visitor-id");
    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    // Get room photo URL from UserPreference
    const userPref = await db.userPreference.findUnique({
      where: { visitorId },
    });

    if (!userPref?.roomPhotoUrl) {
      return NextResponse.json(
        { error: "No room photo found. Please upload a room photo first." },
        { status: 400 }
      );
    }

    // Call Claude Vision API to analyze the room
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image",
              source: {
                type: "url",
                url: userPref.roomPhotoUrl,
              },
            },
            {
              type: "text",
              text: `You are a professional interior decorator. Analyze this room photo to find the BEST spot to hang artwork.

CRITICAL RULES - READ CAREFULLY:
1. NEVER place artwork overlapping ANY glass, windows, or doors - even partially
2. NEVER place artwork on door/window FRAMES or TRIM - those are part of the window/door area
3. Only place on SOLID OPAQUE WALL surfaces with actual wall texture/paint
4. If you can see through it (sky, outside, reflections), it's NOT a wall

STEP 1 - MAP ALL GLASS/WINDOWS/DOORS:
Scan left to right and list EVERY transparent or semi-transparent area:
- Include the full width of each window/door INCLUDING its frame/trim
- Glass French doors count as windows (entire door area is off-limits)
- Arched windows above doors are also off-limits

STEP 2 - IDENTIFY TRUE WALL SECTIONS:
After excluding all glass areas, find remaining SOLID wall:
- Must be actual painted/textured wall surface
- Must be at least 10% of image width
- NOT decorative trim or molding around windows

STEP 3 - CHOOSE BEST PLACEMENT:
If a suitable wall section exists:
- Center the painting on that wall section
- Size appropriately (not too large)
- Place at eye level (30-40% from top)

If NO suitable solid wall exists:
- Set "noSuitableWall": true
- Suggest a small painting on the best available narrow wall strip

Return JSON with ALL coordinates as PERCENTAGES (0-100) of image dimensions:
{
  "glassAreas": [{"left": <% from left>, "right": <% from left>, "type": "<window|door|french door>"}],
  "solidWallSections": [{"left": <% from left>, "right": <% from left>, "width": <% width>}],
  "noSuitableWall": <true|false>,
  "x": <% from left edge - where painting starts>,
  "y": <% from top edge - where painting starts>,
  "width": <% of image width>,
  "height": <% of image height>,
  "recommendedAspect": "<portrait|landscape|square>",
  "recommendedFrame": "<thin black|thin white|natural wood|ornate gold>",
  "needsMat": <true|false>,
  "reasoning": "<explanation of why this spot>"
}

Return ONLY valid JSON, no markdown.`,
            },
          ],
        },
      ],
    });

    // Parse the response
    const content = response.content[0];
    if (content.type !== "text") {
      throw new Error("Unexpected response type from Claude");
    }

    let placement;
    try {
      // Clean up the response in case it has markdown formatting
      let jsonStr = content.text.trim();
      if (jsonStr.startsWith("```json")) {
        jsonStr = jsonStr.slice(7);
      }
      if (jsonStr.startsWith("```")) {
        jsonStr = jsonStr.slice(3);
      }
      if (jsonStr.endsWith("```")) {
        jsonStr = jsonStr.slice(0, -3);
      }
      placement = JSON.parse(jsonStr.trim());
    } catch {
      console.error("Failed to parse Claude response:", content.text);
      // Fall back to default center placement
      placement = {
        x: 35,
        y: 25,
        width: 30,
        height: 30,
        reasoning: "Default center placement (failed to parse AI response)",
      };
    }

    // Store the placement suggestion in the database
    await db.userPreference.update({
      where: { visitorId },
      data: {
        placementSuggestion: placement,
        updatedAt: new Date(),
      },
    });

    console.log(`Room analyzed for ${visitorId}:`, placement);

    return NextResponse.json({
      success: true,
      placement,
    });
  } catch (error) {
    console.error("Error analyzing room:", error);

    // Return a default placement on error so the feature still works
    const defaultPlacement = {
      x: 35,
      y: 25,
      width: 30,
      height: 30,
      reasoning: "Default placement (analysis failed)",
    };

    return NextResponse.json({
      success: false,
      placement: defaultPlacement,
      error: "Failed to analyze room, using default placement",
    });
  }
}
