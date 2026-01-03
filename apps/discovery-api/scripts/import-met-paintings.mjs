import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const MET_API_BASE = 'https://collectionapi.metmuseum.org/public/collection/v1';
const LIMIT = 200;

async function fetchPaintingIds() {
  // Search for paintings with images
  const url = `${MET_API_BASE}/search?hasImages=true&medium=Paintings&q=*`;
  const response = await fetch(url);
  const data = await response.json();
  console.log(`Found ${data.total} paintings total`);
  return data.objectIDs.slice(0, LIMIT);
}

async function fetchPaintingDetails(objectId) {
  const url = `${MET_API_BASE}/objects/${objectId}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch object ${objectId}: ${response.status}`);
  }
  return response.json();
}

function extractYear(objectDate) {
  if (!objectDate) return null;
  // Try to extract a 4-digit year
  const match = objectDate.match(/\b(\d{4})\b/);
  return match ? parseInt(match[1], 10) : null;
}

async function main() {
  console.log('Fetching painting IDs from Met Museum API...');
  const objectIds = await fetchPaintingIds();
  console.log(`Will import ${objectIds.length} paintings\n`);

  let imported = 0;
  let failed = 0;

  for (const objectId of objectIds) {
    try {
      const details = await fetchPaintingDetails(objectId);

      // Skip if no primary image
      if (!details.primaryImage) {
        console.log(`Skipping ${objectId}: no primary image`);
        failed++;
        continue;
      }

      // Check if already exists
      const existing = await prisma.$queryRaw`
        SELECT id FROM paintings WHERE source_url = ${`https://www.metmuseum.org/art/collection/search/${objectId}`}
      `;
      if (existing.length > 0) {
        console.log(`Skipping ${objectId}: already exists`);
        continue;
      }

      // Extract data
      const painting = {
        title: details.title || 'Untitled',
        artist: details.artistDisplayName || 'Unknown',
        year: extractYear(details.objectDate),
        style: details.classification || null,
        description: [
          details.medium,
          details.dimensions,
          details.creditLine,
        ].filter(Boolean).join('. '),
        externalImageUrl: details.primaryImage,
        source: 'The Metropolitan Museum of Art',
        sourceUrl: `https://www.metmuseum.org/art/collection/search/${objectId}`,
        license: details.isPublicDomain ? 'Public Domain' : 'Restricted',
      };

      await prisma.painting.create({ data: painting });
      imported++;
      console.log(`[${imported}/${LIMIT}] Imported: ${painting.title.substring(0, 50)}...`);

      // Small delay to be nice to the API
      await new Promise(r => setTimeout(r, 100));
    } catch (error) {
      console.error(`Error importing ${objectId}:`, error.message);
      failed++;
    }
  }

  console.log(`\nDone! Imported: ${imported}, Failed: ${failed}`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
