export const PRICING = {
  sizes: {
    "40x50": { name: "40×50cm", basePrice: 19900 },   // ¥199
    "50x60": { name: "50×60cm", basePrice: 24900 },   // ¥249
    "60x80": { name: "60×80cm", basePrice: 29900 },   // ¥299
    "80x100": { name: "80×100cm", basePrice: 39900 }, // ¥399
  },
  materials: {
    paper: { name: "高清打印纸", multiplier: 1.0 },
    canvas: { name: "油画布", multiplier: 1.3 },
    textured: { name: "肌理画布", multiplier: 1.6 },
  },
  frames: {
    none: { name: "无框", price: 0 },
    black: { name: "黑色细框", price: 5000 },      // +¥50
    white: { name: "白色细框", price: 5000 },      // +¥50
    wood: { name: "原木框", price: 8000 },         // +¥80
    gold: { name: "金色框", price: 10000 },        // +¥100
  },
} as const;

export type SizeKey = keyof typeof PRICING.sizes;
export type MaterialKey = keyof typeof PRICING.materials;
export type FrameKey = keyof typeof PRICING.frames;

export function calculatePrice(
  size: string,
  material: string,
  frame: string
): number {
  const sizeConfig = PRICING.sizes[size as SizeKey];
  const materialConfig = PRICING.materials[material as MaterialKey];
  const frameConfig = PRICING.frames[frame as FrameKey];

  const basePrice = sizeConfig?.basePrice || 29900;
  const materialMultiplier = materialConfig?.multiplier || 1.0;
  const framePrice = frameConfig?.price || 0;

  return Math.round(basePrice * materialMultiplier) + framePrice;
}

export function formatPrice(cents: number): string {
  return `¥${(cents / 100).toFixed(2)}`;
}
