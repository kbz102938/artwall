import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

const PAGE_SIZE = 100;

// GET: Preview paintings to be deleted (dry run)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get("page") || "1", 10);
    const offset = (page - 1) * PAGE_SIZE;

    // Get total count
    const countResult = await db.$queryRaw<[{ count: bigint }]>`
      SELECT COUNT(*) as count FROM paintings
    `;
    const total = Number(countResult[0].count);
    const totalPages = Math.ceil(total / PAGE_SIZE);

    // Get paintings for this page (ordered by created_at DESC)
    const paintings = await db.$queryRaw<
      { id: string; title: string; created_at: Date }[]
    >`
      SELECT id, title, created_at
      FROM paintings
      ORDER BY created_at DESC
      LIMIT ${PAGE_SIZE} OFFSET ${offset}
    `;

    return NextResponse.json({
      page,
      pageSize: PAGE_SIZE,
      total,
      totalPages,
      count: paintings.length,
      paintings: paintings.map((p) => ({
        id: p.id,
        title: p.title,
        createdAt: p.created_at,
      })),
    });
  } catch (error) {
    console.error("Error fetching paintings:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// DELETE: Delete paintings by page
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get("page") || "1", 10);
    const offset = (page - 1) * PAGE_SIZE;

    // Get painting IDs to delete (ordered by created_at DESC)
    const paintings = await db.$queryRaw<{ id: string }[]>`
      SELECT id FROM paintings
      ORDER BY created_at DESC
      LIMIT ${PAGE_SIZE} OFFSET ${offset}
    `;

    if (paintings.length === 0) {
      return NextResponse.json({
        message: "No paintings found for this page",
        deleted: 0,
      });
    }

    const ids = paintings.map((p) => p.id);

    // Delete related records first (foreign key constraints)
    await db.$executeRaw`DELETE FROM shown_paintings WHERE painting_id = ANY(${ids}::text[])`;
    await db.$executeRaw`DELETE FROM saved_paintings WHERE painting_id = ANY(${ids}::text[])`;
    await db.$executeRaw`DELETE FROM activities WHERE painting_id = ANY(${ids}::text[])`;

    // Check for orders - don't delete paintings with orders
    const ordersCount = await db.$queryRaw<[{ count: bigint }]>`
      SELECT COUNT(*) as count FROM orders WHERE painting_id = ANY(${ids}::text[])
    `;

    if (Number(ordersCount[0].count) > 0) {
      // Filter out paintings with orders
      const paintingsWithOrders = await db.$queryRaw<{ painting_id: string }[]>`
        SELECT DISTINCT painting_id FROM orders WHERE painting_id = ANY(${ids}::text[])
      `;
      const orderPaintingIds = new Set(paintingsWithOrders.map((p) => p.painting_id));
      const idsToDelete = ids.filter((id) => !orderPaintingIds.has(id));

      if (idsToDelete.length > 0) {
        await db.$executeRaw`DELETE FROM paintings WHERE id = ANY(${idsToDelete}::text[])`;
      }

      return NextResponse.json({
        message: `Deleted ${idsToDelete.length} paintings, skipped ${orderPaintingIds.size} with orders`,
        deleted: idsToDelete.length,
        skipped: Array.from(orderPaintingIds),
      });
    }

    // Delete paintings
    await db.$executeRaw`DELETE FROM paintings WHERE id = ANY(${ids}::text[])`;

    return NextResponse.json({
      message: `Deleted ${ids.length} paintings from page ${page}`,
      deleted: ids.length,
      ids,
    });
  } catch (error) {
    console.error("Error deleting paintings:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
