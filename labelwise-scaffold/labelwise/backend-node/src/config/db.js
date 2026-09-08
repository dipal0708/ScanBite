import pg from "pg";

const { Pool } = pg;

// Reads standard PG* env vars, or DATABASE_URL if set.
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

pool.on("error", (err) => {
  console.error("Unexpected Postgres error", err);
});
