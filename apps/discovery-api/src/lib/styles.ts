export interface HomeStyle {
  code: string;
  name: string;
  nameEn: string;
  imageUrl: string;
  keywords: string[];
  // Embedding will be pre-computed and added later
  embedding?: number[];
}

export const HOME_STYLES: HomeStyle[] = [
  {
    code: "modern",
    name: "现代简约",
    nameEn: "Modern Minimalist",
    imageUrl: "/images/styles/modern.jpg",
    keywords: ["黑白灰", "线条感", "少即是多"],
  },
  {
    code: "nordic",
    name: "北欧",
    nameEn: "Nordic",
    imageUrl: "/images/styles/nordic.jpg",
    keywords: ["白色", "木质", "绿植", "温暖"],
  },
  {
    code: "japanese",
    name: "日式/侘寂",
    nameEn: "Japanese Wabi-Sabi",
    imageUrl: "/images/styles/japanese.jpg",
    keywords: ["原木", "低饱和", "自然", "禅意"],
  },
  {
    code: "chinese",
    name: "新中式",
    nameEn: "New Chinese",
    imageUrl: "/images/styles/chinese.jpg",
    keywords: ["木质", "对称", "留白", "东方元素"],
  },
  {
    code: "french",
    name: "法式/轻奢",
    nameEn: "French Luxury",
    imageUrl: "/images/styles/french.jpg",
    keywords: ["石膏线", "金色点缀", "优雅"],
  },
  {
    code: "american",
    name: "美式",
    nameEn: "American",
    imageUrl: "/images/styles/american.jpg",
    keywords: ["深色木质", "复古", "厚重"],
  },
  {
    code: "industrial",
    name: "工业风",
    nameEn: "Industrial",
    imageUrl: "/images/styles/industrial.jpg",
    keywords: ["水泥", "金属", "裸露管道"],
  },
  {
    code: "cream",
    name: "奶油风/混搭",
    nameEn: "Cream/Eclectic",
    imageUrl: "/images/styles/cream.jpg",
    keywords: ["柔和色调", "舒适", "无明显风格"],
  },
];

export function getStyleByCode(code: string): HomeStyle | undefined {
  return HOME_STYLES.find((s) => s.code === code);
}

export function getStylesByCodes(codes: string[]): HomeStyle[] {
  return HOME_STYLES.filter((s) => codes.includes(s.code));
}

// Placeholder: Average embeddings for selected styles
// This will be replaced with actual CLIP embeddings
export function getStyleEmbedding(codes: string[]): number[] | null {
  const styles = getStylesByCodes(codes);

  if (styles.length === 0) {
    return null;
  }

  // Check if all selected styles have embeddings
  const embeddings = styles
    .map((s) => s.embedding)
    .filter((e): e is number[] => e !== undefined);

  if (embeddings.length === 0) {
    return null;
  }

  // Average the embeddings
  const dim = embeddings[0].length;
  const result = new Array(dim).fill(0);

  for (const emb of embeddings) {
    for (let i = 0; i < dim; i++) {
      result[i] += emb[i] / embeddings.length;
    }
  }

  // Normalize to unit vector
  const norm = Math.sqrt(result.reduce((sum, v) => sum + v * v, 0));
  if (norm > 0) {
    return result.map((v) => v / norm);
  }

  return result;
}
