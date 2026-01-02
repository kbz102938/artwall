/**
 * Generate CLIP embeddings for home style images and update the database.
 *
 * Usage:
 *   npx ts-node scripts/generate_style_embeddings.ts
 *
 * Prerequisites:
 *   - Style images must be publicly accessible
 *   - CLIP service must be running
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Configuration
const CLIP_SERVICE_URL = process.env.CLIP_SERVICE_URL || 'https://clip-service-919123660014.us-central1.run.app';
const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || 'https://artwall-web-919123660014.us-central1.run.app';

interface StyleRow {
  id: number;
  name: string;
  image_url: string;
}

async function getEmbedding(imageUrl: string): Promise<number[]> {
  const response = await fetch(`${CLIP_SERVICE_URL}/api/embedding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ imageUrl }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`CLIP service error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  return data.embedding;
}

async function main() {
  console.log('🎨 Generating embeddings for home styles...\n');
  console.log(`CLIP Service: ${CLIP_SERVICE_URL}`);
  console.log(`Frontend URL: ${FRONTEND_BASE_URL}\n`);

  // Get all styles
  const styles = await prisma.$queryRaw<StyleRow[]>`
    SELECT id, name, image_url FROM home_styles ORDER BY id
  `;

  console.log(`Found ${styles.length} styles to process\n`);

  let success = 0;
  let failed = 0;

  for (const style of styles) {
    const fullImageUrl = `${FRONTEND_BASE_URL}${style.image_url}`;

    try {
      console.log(`Processing: ${style.name} (ID: ${style.id})`);
      console.log(`  Image: ${fullImageUrl}`);

      const embedding = await getEmbedding(fullImageUrl);
      const embeddingStr = `[${embedding.join(',')}]`;

      await prisma.$executeRawUnsafe(`
        UPDATE home_styles
        SET embedding = $1::vector
        WHERE id = $2
      `, embeddingStr, style.id);

      console.log(`  ✅ Embedding generated (${embedding.length} dimensions)\n`);
      success++;
    } catch (error) {
      console.log(`  ❌ Failed: ${error instanceof Error ? error.message : 'Unknown error'}\n`);
      failed++;
    }
  }

  console.log('---');
  console.log(`Done! Success: ${success}, Failed: ${failed}`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
