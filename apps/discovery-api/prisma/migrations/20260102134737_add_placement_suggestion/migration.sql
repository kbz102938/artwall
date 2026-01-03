/*
  Warnings:

  - You are about to drop the column `last_style_codes` on the `user_preferences` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "user_preferences" DROP COLUMN "last_style_codes",
ADD COLUMN     "placement_suggestion" JSONB;

-- CreateTable
CREATE TABLE "home_styles" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "name_en" TEXT,
    "image_url" TEXT NOT NULL,
    "embedding" vector(512) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "home_styles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_style_selections" (
    "visitor_id" TEXT NOT NULL,
    "style_id" INTEGER NOT NULL,
    "selected_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_style_selections_pkey" PRIMARY KEY ("visitor_id","style_id")
);

-- CreateIndex
CREATE INDEX "user_style_selections_visitor_id_idx" ON "user_style_selections"("visitor_id");

-- AddForeignKey
ALTER TABLE "user_style_selections" ADD CONSTRAINT "user_style_selections_visitor_id_fkey" FOREIGN KEY ("visitor_id") REFERENCES "user_preferences"("visitor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_style_selections" ADD CONSTRAINT "user_style_selections_style_id_fkey" FOREIGN KEY ("style_id") REFERENCES "home_styles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
