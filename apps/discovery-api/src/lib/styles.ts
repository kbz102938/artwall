/**
 * Home styles are now stored in the database (home_styles table).
 *
 * Schema:
 * - id: number (PK)
 * - name: string (Chinese name)
 * - name_en: string (English name)
 * - image_url: string (style image URL)
 * - embedding: vector(512) (pre-computed CLIP embedding)
 *
 * User selections are stored in user_style_selections table.
 * Feed recommendations use MAX similarity across selected style embeddings.
 */

export {};
