import { NextResponse } from "next/server";
import { Storage } from "@google-cloud/storage";
import { db } from "@/lib/db";

const storage = new Storage();
const BUCKET_NAME = "artwall-artwork";
const GCS_PREFIX = "https://storage.googleapis.com/";

export async function POST() {
  try {
    // Find paintings that need migration:
    // - Have external_image_url
    // - image_url is NULL or not on GCS
    const paintings = await db.$queryRaw<
      { id: string; external_image_url: string; image_url: string | null }[]
    >`
      SELECT id, external_image_url, image_url
      FROM paintings
      WHERE external_image_url IS NOT NULL
        AND (image_url IS NULL OR image_url NOT LIKE ${GCS_PREFIX + "%"})
    `;

    if (paintings.length === 0) {
      return NextResponse.json({
        message: "No paintings need migration",
        processed: 0,
        failed: [],
      });
    }

    console.log(`Found ${paintings.length} paintings to migrate`);

    const results: { id: string; success: boolean; error?: string }[] = [];
    const bucket = storage.bucket(BUCKET_NAME);

    for (const painting of paintings) {
      try {
        console.log(`Migrating ${painting.id}...`);

        // Download image from external URL
        const response = await fetch(painting.external_image_url);
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }

        const contentType = response.headers.get("content-type") || "image/jpeg";
        const buffer = Buffer.from(await response.arrayBuffer());

        // Determine file extension
        let ext = "jpg";
        if (contentType.includes("png")) ext = "png";
        else if (contentType.includes("webp")) ext = "webp";
        else if (contentType.includes("gif")) ext = "gif";

        // Upload to GCS
        const filePath = `paintings/${painting.id}.${ext}`;
        const blob = bucket.file(filePath);

        await blob.save(buffer, {
          metadata: { contentType },
        });

        const gcsUrl = `${GCS_PREFIX}${BUCKET_NAME}/${filePath}`;

        // Update database
        await db.$executeRaw`
          UPDATE paintings
          SET image_url = ${gcsUrl}, updated_at = NOW()
          WHERE id = ${painting.id}
        `;

        console.log(`  -> ${gcsUrl}`);
        results.push({ id: painting.id, success: true });
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        console.error(`  Error: ${errorMsg}`);
        results.push({ id: painting.id, success: false, error: errorMsg });
      }
    }

    const processed = results.filter((r) => r.success).length;
    const failed = results.filter((r) => !r.success);

    return NextResponse.json({
      message: `Migration complete`,
      processed,
      total: paintings.length,
      failed: failed.map((f) => ({ id: f.id, error: f.error })),
    });
  } catch (error) {
    console.error("Migration error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
