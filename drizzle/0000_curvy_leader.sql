CREATE TYPE "public"."diagnostic_status" AS ENUM('draft', 'running', 'complete', 'failed');--> statement-breakpoint
CREATE TABLE "diagnostic_runs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"owner_id" uuid,
	"title" text NOT NULL,
	"status" "diagnostic_status" DEFAULT 'draft' NOT NULL,
	"input" jsonb,
	"result" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "diagnostic_runs_owner_id_idx" ON "diagnostic_runs" USING btree ("owner_id");--> statement-breakpoint
CREATE INDEX "diagnostic_runs_status_idx" ON "diagnostic_runs" USING btree ("status");