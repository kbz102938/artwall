#!/bin/bash

# Generate CLIP embeddings for home style images

CLIP_SERVICE="https://clip-service-919123660014.us-central1.run.app"
GCS_BASE="https://storage.googleapis.com/artwall-user-content/styles"

# Style mappings: name -> filename
declare -A STYLES=(
  ["现代简约"]="现代简约风.JPG"
  ["北欧"]="北欧风.JPG"
  ["日式侘寂"]="侘寂风.JPG"
  ["新中式"]="新中式.JPG"
  ["法式"]="法式风.JPG"
  ["中古风"]="中古风.JPG"
  ["包豪斯"]="包豪斯.JPG"
  ["南洋复古"]="南洋复古.JPG"
  ["原木风"]="原木风.JPG"
  ["多巴胺"]="多巴胺风.JPG"
  ["奶油风"]="奶油风.JPG"
  ["宋氏美学"]="宋氏美学.JPG"
  ["意式风"]="意式风.JPG"
  ["极简风"]="极简风.JPG"
  ["混搭风"]="混搭风.JPG"
  ["轻奢风"]="轻奢风.JPG"
)

echo "🎨 Generating embeddings for home styles..."
echo ""

for name in "${!STYLES[@]}"; do
  filename="${STYLES[$name]}"
  # URL encode the filename
  encoded_filename=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$filename'))")
  image_url="${GCS_BASE}/${encoded_filename}"

  echo "Processing: $name"
  echo "  URL: $image_url"

  # Get embedding from CLIP service
  response=$(curl -s -X POST "${CLIP_SERVICE}/api/embedding" \
    -H "Content-Type: application/json" \
    -d "{\"imageUrl\": \"$image_url\"}")

  # Check if we got an embedding
  if echo "$response" | grep -q '"embedding"'; then
    # Extract embedding array and format for PostgreSQL
    embedding=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('[' + ','.join(map(str, data['embedding'])) + ']')")

    echo "  ✅ Got embedding (512 dimensions)"

    # Update database - escape the name for SQL
    escaped_name=$(echo "$name" | sed "s/'/''/g")

    npx prisma db execute --schema prisma/schema.prisma --stdin <<EOF
UPDATE home_styles SET embedding = '${embedding}'::vector WHERE name = '${escaped_name}';
EOF

  else
    echo "  ❌ Failed: $response"
  fi

  echo ""
done

echo "Done!"
