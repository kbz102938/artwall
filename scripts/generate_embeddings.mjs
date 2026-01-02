/**
 * Generate CLIP embeddings for home style images
 * Run: node scripts/generate_embeddings.mjs
 */

const CLIP_SERVICE = 'https://clip-service-919123660014.us-central1.run.app';

const styles = [
  { name: '现代简约', file: '现代简约风.JPG' },
  { name: '北欧', file: '北欧风.JPG' },
  { name: '日式侘寂', file: '侘寂风.JPG' },
  { name: '新中式', file: '新中式.JPG' },
  { name: '法式', file: '法式风.JPG' },
  { name: '中古风', file: '中古风.JPG' },
  { name: '包豪斯', file: '包豪斯.JPG' },
  { name: '南洋复古', file: '南洋复古.JPG' },
  { name: '原木风', file: '原木风.JPG' },
  { name: '多巴胺', file: '多巴胺风.JPG' },
  { name: '奶油风', file: '奶油风.JPG' },
  { name: '宋氏美学', file: '宋氏美学.JPG' },
  { name: '意式风', file: '意式风.JPG' },
  { name: '极简风', file: '极简风.JPG' },
  { name: '混搭风', file: '混搭风.JPG' },
  { name: '轻奢风', file: '轻奢风.JPG' },
];

async function getEmbedding(imageUrl) {
  const response = await fetch(`${CLIP_SERVICE}/api/embedding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ imageUrl }),
  });

  if (!response.ok) {
    throw new Error(`CLIP error: ${response.status}`);
  }

  const data = await response.json();
  return data.embedding;
}

async function main() {
  console.log('🎨 Generating embeddings for home styles...\n');

  const results = [];

  for (const style of styles) {
    const encodedFile = encodeURIComponent(style.file);
    const imageUrl = `https://storage.googleapis.com/artwall-user-content/styles/${encodedFile}`;

    console.log(`Processing: ${style.name}`);

    try {
      const embedding = await getEmbedding(imageUrl);
      console.log(`  ✅ Got ${embedding.length} dimensions`);
      results.push({ name: style.name, embedding });
    } catch (error) {
      console.log(`  ❌ Failed: ${error.message}`);
    }
  }

  // Output SQL statements
  console.log('\n--- SQL UPDATE STATEMENTS ---\n');

  for (const { name, embedding } of results) {
    const embeddingStr = `[${embedding.join(',')}]`;
    const escapedName = name.replace(/'/g, "''");
    console.log(`UPDATE home_styles SET embedding = '${embeddingStr}'::vector WHERE name = '${escapedName}';`);
  }

  console.log('\n--- Done! ---');
}

main().catch(console.error);
