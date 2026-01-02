import { NextRequest, NextResponse } from "next/server";
import { Storage } from "@google-cloud/storage";
import { db } from "@/lib/db";

const storage = new Storage();
const BUCKET_NAME = "artwall-user-content";

export async function POST(request: NextRequest) {
  try {
    const visitorId = request.headers.get("x-visitor-id");
    if (!visitorId) {
      return NextResponse.json(
        { error: "Visitor ID required" },
        { status: 400 }
      );
    }

    // Parse multipart form data
    const formData = await request.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.type.startsWith("image/")) {
      return NextResponse.json(
        { error: "File must be an image" },
        { status: 400 }
      );
    }

    // Validate file size (max 10MB)
    const MAX_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      return NextResponse.json(
        { error: "File size must be less than 10MB" },
        { status: 400 }
      );
    }

    // Generate file path: room-photos/{visitorId}/{timestamp}.{ext}
    const ext = file.type.split("/")[1] || "jpg";
    const timestamp = Date.now();
    const filePath = `room-photos/${visitorId}/${timestamp}.${ext}`;

    // Upload to GCS
    const bucket = storage.bucket(BUCKET_NAME);
    const blob = bucket.file(filePath);

    const buffer = Buffer.from(await file.arrayBuffer());

    await blob.save(buffer, {
      metadata: {
        contentType: file.type,
      },
    });

    // Generate the public URL
    const imageUrl = `https://storage.googleapis.com/${BUCKET_NAME}/${filePath}`;

    // Update user preference with room photo URL
    await db.userPreference.upsert({
      where: { visitorId },
      create: {
        visitorId,
        roomPhotoUrl: imageUrl,
        interactionCount: 0,
      },
      update: {
        roomPhotoUrl: imageUrl,
        updatedAt: new Date(),
      },
    });

    console.log(`Room photo uploaded by ${visitorId}: ${imageUrl}`);

    return NextResponse.json({
      success: true,
      imageUrl,
    });
  } catch (error) {
    console.error("Error uploading room photo:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
