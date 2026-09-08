import { z } from "zod";
import { pool } from "../config/db.js";

// Matches the diet taxonomy from the product spec.
export const DIET_TYPES = [
  "vegan",
  "vegan_no_roots", // excludes onion, garlic, ginger, and other roots/alliums
  "vegetarian",
  "vegetarian_with_eggs",
  "non_vegetarian",
];

export const MEAT_SUBPREFS = ["white_meat", "red_meat", "chicken", "pork", "seafood"];

const profileSchema = z.object({
  dietType: z.enum(DIET_TYPES),
  meatSubprefs: z.array(z.enum(MEAT_SUBPREFS)).optional().default([]),
  healthFlags: z.array(z.string()).optional().default([]),
  allergens: z.array(z.string()).optional().default([]),
  sugarSensitivity: z.number().min(0).max(10).optional().default(5),
  ageBand: z.string().optional(),
  sex: z.string().optional(),
  activityLevel: z.string().optional(),
});

export async function getProfile(req, res, next) {
  try {
    const result = await pool.query("SELECT * FROM profiles WHERE user_id = $1", [req.userId]);
    if (result.rowCount === 0) {
      return res.status(404).json({ error: "No profile set up yet." });
    }
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
}

export async function upsertProfile(req, res, next) {
  try {
    const data = profileSchema.parse(req.body);

    const result = await pool.query(
      `INSERT INTO profiles (
         user_id, diet_type, meat_subprefs, health_flags, allergens,
         sugar_sensitivity, age_band, sex, activity_level, updated_at
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9, now())
       ON CONFLICT (user_id) DO UPDATE SET
         diet_type = EXCLUDED.diet_type,
         meat_subprefs = EXCLUDED.meat_subprefs,
         health_flags = EXCLUDED.health_flags,
         allergens = EXCLUDED.allergens,
         sugar_sensitivity = EXCLUDED.sugar_sensitivity,
         age_band = EXCLUDED.age_band,
         sex = EXCLUDED.sex,
         activity_level = EXCLUDED.activity_level,
         updated_at = now()
       RETURNING *`,
      [
        req.userId,
        data.dietType,
        data.meatSubprefs,
        data.healthFlags,
        data.allergens,
        data.sugarSensitivity,
        data.ageBand,
        data.sex,
        data.activityLevel,
      ]
    );

    res.json(result.rows[0]);
  } catch (err) {
    if (err.name === "ZodError") {
      return res.status(400).json({ error: err.errors[0].message });
    }
    next(err);
  }
}
