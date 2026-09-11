import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";

import * as schema from "./schema";

const globalForDb = globalThis as unknown as {
  queryClient?: ReturnType<typeof postgres>;
};

export function getDb() {
  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error(
      "DATABASE_URL is not configured. Add it to .env.local before querying the database.",
    );
  }

  const queryClient =
    globalForDb.queryClient ?? postgres(databaseUrl, { prepare: false });

  if (process.env.NODE_ENV !== "production") {
    globalForDb.queryClient = queryClient;
  }

  return drizzle(queryClient, { schema });
}
