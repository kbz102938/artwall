-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "vector";

-- CreateTable
CREATE TABLE "paintings" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "title_en" TEXT,
    "artist" TEXT NOT NULL,
    "artist_en" TEXT,
    "year" INTEGER,
    "style" TEXT,
    "image_url" TEXT NOT NULL,
    "image_hd_url" TEXT,
    "source" TEXT,
    "source_url" TEXT,
    "license" TEXT,
    "embedding" vector(512),
    "tags" TEXT[],
    "aspect_ratio" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "paintings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_preferences" (
    "visitor_id" TEXT NOT NULL,
    "embedding" vector(512),
    "interaction_count" INTEGER NOT NULL DEFAULT 0,
    "last_style_codes" TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "user_preferences_pkey" PRIMARY KEY ("visitor_id")
);

-- CreateTable
CREATE TABLE "activities" (
    "id" BIGSERIAL NOT NULL,
    "visitor_id" TEXT NOT NULL,
    "session_id" TEXT,
    "event" TEXT NOT NULL,
    "painting_id" TEXT,
    "position" INTEGER,
    "source" TEXT,
    "metadata" JSONB,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "activities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "shown_paintings" (
    "visitor_id" TEXT NOT NULL,
    "painting_id" TEXT NOT NULL,
    "shown_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "shown_paintings_pkey" PRIMARY KEY ("visitor_id","painting_id")
);

-- CreateTable
CREATE TABLE "saved_paintings" (
    "visitor_id" TEXT NOT NULL,
    "painting_id" TEXT NOT NULL,
    "saved_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "saved_paintings_pkey" PRIMARY KEY ("visitor_id","painting_id")
);

-- CreateTable
CREATE TABLE "orders" (
    "id" TEXT NOT NULL,
    "visitor_id" TEXT NOT NULL,
    "stripe_session_id" TEXT,
    "stripe_payment_intent" TEXT,
    "painting_id" TEXT NOT NULL,
    "size" TEXT NOT NULL,
    "material" TEXT NOT NULL DEFAULT 'canvas',
    "frame" TEXT,
    "amount" INTEGER NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'cny',
    "status" TEXT NOT NULL DEFAULT 'pending',
    "shipping_name" TEXT,
    "shipping_phone" TEXT,
    "shipping_address" TEXT,
    "shipping_tracking" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "paid_at" TIMESTAMP(3),
    "shipped_at" TIMESTAMP(3),
    "delivered_at" TIMESTAMP(3),
    "metadata" JSONB,

    CONSTRAINT "orders_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "batch_jobs" (
    "id" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "total" INTEGER NOT NULL DEFAULT 0,
    "processed" INTEGER NOT NULL DEFAULT 0,
    "failed" INTEGER NOT NULL DEFAULT 0,
    "failed_items" JSONB,
    "error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),

    CONSTRAINT "batch_jobs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "activities_visitor_id_created_at_idx" ON "activities"("visitor_id", "created_at" DESC);

-- CreateIndex
CREATE INDEX "activities_processed_created_at_idx" ON "activities"("processed", "created_at");

-- CreateIndex
CREATE INDEX "shown_paintings_visitor_id_idx" ON "shown_paintings"("visitor_id");

-- CreateIndex
CREATE UNIQUE INDEX "orders_stripe_session_id_key" ON "orders"("stripe_session_id");

-- CreateIndex
CREATE INDEX "orders_visitor_id_created_at_idx" ON "orders"("visitor_id", "created_at" DESC);

-- CreateIndex
CREATE INDEX "orders_status_idx" ON "orders"("status");

-- AddForeignKey
ALTER TABLE "activities" ADD CONSTRAINT "activities_visitor_id_fkey" FOREIGN KEY ("visitor_id") REFERENCES "user_preferences"("visitor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "activities" ADD CONSTRAINT "activities_painting_id_fkey" FOREIGN KEY ("painting_id") REFERENCES "paintings"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shown_paintings" ADD CONSTRAINT "shown_paintings_visitor_id_fkey" FOREIGN KEY ("visitor_id") REFERENCES "user_preferences"("visitor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shown_paintings" ADD CONSTRAINT "shown_paintings_painting_id_fkey" FOREIGN KEY ("painting_id") REFERENCES "paintings"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "saved_paintings" ADD CONSTRAINT "saved_paintings_visitor_id_fkey" FOREIGN KEY ("visitor_id") REFERENCES "user_preferences"("visitor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "saved_paintings" ADD CONSTRAINT "saved_paintings_painting_id_fkey" FOREIGN KEY ("painting_id") REFERENCES "paintings"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "orders" ADD CONSTRAINT "orders_visitor_id_fkey" FOREIGN KEY ("visitor_id") REFERENCES "user_preferences"("visitor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "orders" ADD CONSTRAINT "orders_painting_id_fkey" FOREIGN KEY ("painting_id") REFERENCES "paintings"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
