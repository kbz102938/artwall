import { NextResponse } from "next/server";
import { db } from "@/lib/db";

const CLIP_SERVICE_URL = "https://clip-service-919123660014.us-central1.run.app";

// Check if embedding is all zeros (placeholder)
function isZeroEmbedding(embeddingStr: string | null): boolean {
  if (!embeddingStr) return true;
  // Embedding format: "[0,0,0,...]"
  const values = embeddingStr.slice(1, -1).split(",").map(Number);
  return values.every((v) => v === 0);
}

export async function POST() {
  try {
    // Find paintings that need embeddings:
    // - Have image_url (preferably GCS)
    // - embedding IS NULL or is all zeros
    const paintings = await db.$queryRaw<
      { id: string; image_url: string; external_image_url: string | null; embedding: string | null }[]
    >`
      SELECT id, image_url, external_image_url, embedding::text
      FROM paintings
      WHERE image_url IS NOT NULL
    `;

    // Filter to only paintings needing embeddings
    const needsEmbedding = paintings.filter(
      (p) => !p.embedding || isZeroEmbedding(p.embedding)
    );

    if (needsEmbedding.length === 0) {
      return NextResponse.json({
        message: "No paintings need embeddings",
        processed: 0,
        failed: [],
      });
    }

    console.log(`Found ${needsEmbedding.length} paintings needing embeddings`);

    const results: { id: string; success: boolean; error?: string }[] = [];

    for (const painting of needsEmbedding) {
      try {
        console.log(`Generating embedding for ${painting.id}...`);

        // Use image_url (GCS) if available, otherwise external_image_url
        const imageUrl = painting.image_url || painting.external_image_url;
        if (!imageUrl) {
          throw new Error("No image URL available");
        }

        // Call CLIP service
        const response = await fetch(`${CLIP_SERVICE_URL}/api/embedding`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ imageUrl }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`CLIP service error: ${response.status} - ${errorText}`);
        }

        const { embedding } = await response.json();

        if (!embedding || !Array.isArray(embedding)) {
          throw new Error("Invalid embedding response");
        }

        // Format embedding for pgvector
        const embeddingStr = "[" + embedding.join(",") + "]";

        // Update database
        await db.$executeRaw`
          UPDATE paintings
          SET embedding = ${embeddingStr}::vector, updated_at = NOW()
          WHERE id = ${painting.id}
        `;

        console.log(`  -> ${embedding.length} dimensions`);
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
      message: `Embedding generation complete`,
      processed,
      total: needsEmbedding.length,
      failed: failed.map((f) => ({ id: f.id, error: f.error })),
    });
  } catch (error) {
    console.error("Embedding generation error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
