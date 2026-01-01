import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

const CLIP_SERVICE_URL = process.env.CLIP_SERVICE_URL || "http://localhost:8080";

interface PaintingInput {
  id: string;
  title: string;
  titleEn?: string;
  artist: string;
  artistEn?: string;
  year?: number;
  style?: string;
  imageUrl: string;
  imageHdUrl?: string;
  source?: string;
  sourceUrl?: string;
  license?: string;
  tags?: string[];
  aspectRatio?: string;
}

interface BatchResult {
  id: string;
  success: boolean;
  error?: string;
}

// POST /api/admin/paintings/batch - Batch upload paintings with embeddings
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { paintings } = body as { paintings: PaintingInput[] };

    if (!paintings || !Array.isArray(paintings) || paintings.length === 0) {
      return NextResponse.json(
        { error: "No paintings provided" },
        { status: 400 }
      );
    }

    // Create batch job
    const jobId = `job_${Date.now()}`;
    await db.batchJob.create({
      data: {
        id: jobId,
        status: "processing",
        total: paintings.length,
      },
    });

    // Process paintings - get embeddings and insert
    const results: BatchResult[] = [];
    let processed = 0;
    let failed = 0;

    for (const painting of paintings) {
      try {
        // Get embedding from CLIP service
        const embeddingResponse = await fetch(`${CLIP_SERVICE_URL}/api/embedding`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ imageUrl: painting.imageUrl }),
        });

        if (!embeddingResponse.ok) {
          throw new Error(`CLIP service error: ${embeddingResponse.status}`);
        }

        const { embedding } = await embeddingResponse.json();
        const embeddingStr = `[${embedding.join(",")}]`;

        // Insert painting with embedding using raw SQL
        await db.$executeRawUnsafe(`
          INSERT INTO paintings (
            id, title, title_en, artist, artist_en, year, style,
            image_url, image_hd_url, source, source_url, license,
            tags, aspect_ratio, embedding, created_at, updated_at
          ) VALUES (
            $1, $2, $3, $4, $5, $6, $7,
            $8, $9, $10, $11, $12,
            $13, $14, $15::vector, NOW(), NOW()
          )
          ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            embedding = EXCLUDED.embedding,
            updated_at = NOW()
        `,
          painting.id,
          painting.title,
          painting.titleEn || null,
          painting.artist,
          painting.artistEn || null,
          painting.year || null,
          painting.style || null,
          painting.imageUrl,
          painting.imageHdUrl || null,
          painting.source || null,
          painting.sourceUrl || null,
          painting.license || null,
          painting.tags || [],
          painting.aspectRatio || null,
          embeddingStr
        );

        results.push({ id: painting.id, success: true });
        processed++;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        results.push({ id: painting.id, success: false, error: errorMessage });
        failed++;
      }
    }

    // Update batch job status
    const failedResults = results.filter((r) => !r.success);
    await db.batchJob.update({
      where: { id: jobId },
      data: {
        status: "completed",
        processed,
        failed,
        failedItems: failedResults.length > 0 ? JSON.parse(JSON.stringify({ items: failedResults })) : undefined,
        completedAt: new Date(),
      },
    });

    return NextResponse.json({
      jobId,
      status: "completed",
      total: paintings.length,
      processed,
      failed,
      results,
    });
  } catch (error) {
    console.error("Error in batch upload:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// GET /api/admin/paintings/batch?jobId=xxx - Check batch job status
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      // Return all recent jobs
      const jobs = await db.batchJob.findMany({
        orderBy: { createdAt: "desc" },
        take: 10,
      });
      return NextResponse.json({ jobs });
    }

    const job = await db.batchJob.findUnique({
      where: { id: jobId },
    });

    if (!job) {
      return NextResponse.json(
        { error: "Job not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({ job });
  } catch (error) {
    console.error("Error fetching batch job:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
