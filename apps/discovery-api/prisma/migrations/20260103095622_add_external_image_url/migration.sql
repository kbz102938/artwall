-- AlterTable
ALTER TABLE "paintings" ADD COLUMN     "external_image_url" TEXT,
ALTER COLUMN "image_url" DROP NOT NULL;

-- Copy existing image_url to external_image_url (preserve original sources)
UPDATE "paintings" SET "external_image_url" = "image_url" WHERE "image_url" IS NOT NULL;
