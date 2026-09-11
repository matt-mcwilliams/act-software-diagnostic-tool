import {
  index,
  jsonb,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

export const diagnosticStatus = pgEnum("diagnostic_status", [
  "draft",
  "running",
  "complete",
  "failed",
]);

export const diagnosticRuns = pgTable(
  "diagnostic_runs",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    ownerId: uuid("owner_id"),
    title: text("title").notNull(),
    status: diagnosticStatus("status").default("draft").notNull(),
    input: jsonb("input").$type<Record<string, unknown>>(),
    result: jsonb("result").$type<Record<string, unknown>>(),
    createdAt: timestamp("created_at", {
      withTimezone: true,
      mode: "date",
    })
      .defaultNow()
      .notNull(),
    updatedAt: timestamp("updated_at", {
      withTimezone: true,
      mode: "date",
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index("diagnostic_runs_owner_id_idx").on(table.ownerId),
    index("diagnostic_runs_status_idx").on(table.status),
  ],
);

export type DiagnosticRun = typeof diagnosticRuns.$inferSelect;
export type NewDiagnosticRun = typeof diagnosticRuns.$inferInsert;
