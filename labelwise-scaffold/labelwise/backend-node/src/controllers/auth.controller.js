import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { z } from "zod";
import { pool } from "../config/db.js";

const JWT_SECRET = process.env.JWT_SECRET || "dev_secret";
const ACCESS_TTL = "15m";
const REFRESH_TTL = "30d";

const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "Password must be at least 8 characters"),
  displayName: z.string().min(1).max(80),
});

function issueTokens(userId) {
  const accessToken = jwt.sign({ sub: userId }, JWT_SECRET, { expiresIn: ACCESS_TTL });
  const refreshToken = jwt.sign({ sub: userId, type: "refresh" }, JWT_SECRET, {
    expiresIn: REFRESH_TTL,
  });
  return { accessToken, refreshToken };
}

export async function signup(req, res, next) {
  try {
    const { email, password, displayName } = signupSchema.parse(req.body);

    const existing = await pool.query("SELECT id FROM users WHERE email = $1", [email]);
    if (existing.rowCount > 0) {
      return res.status(409).json({ error: "An account with this email already exists." });
    }

    const passwordHash = await bcrypt.hash(password, 12);
    const result = await pool.query(
      `INSERT INTO users (email, password_hash, display_name)
       VALUES ($1, $2, $3) RETURNING id, email, display_name`,
      [email, passwordHash, displayName]
    );

    const user = result.rows[0];
    const tokens = issueTokens(user.id);

    res.status(201).json({ user, ...tokens });
  } catch (err) {
    if (err.name === "ZodError") {
      return res.status(400).json({ error: err.errors[0].message });
    }
    next(err);
  }
}

export async function login(req, res, next) {
  try {
    const { email, password } = z
      .object({ email: z.string().email(), password: z.string() })
      .parse(req.body);

    const result = await pool.query(
      "SELECT id, email, display_name, password_hash FROM users WHERE email = $1",
      [email]
    );
    const user = result.rows[0];

    const valid = user && (await bcrypt.compare(password, user.password_hash));
    if (!valid) {
      return res.status(401).json({ error: "Incorrect email or password." });
    }

    const tokens = issueTokens(user.id);
    res.json({
      user: { id: user.id, email: user.email, display_name: user.display_name },
      ...tokens,
    });
  } catch (err) {
    next(err);
  }
}

export async function refresh(req, res, next) {
  try {
    const { refreshToken } = req.body;
    const payload = jwt.verify(refreshToken, JWT_SECRET);
    if (payload.type !== "refresh") throw new Error("Not a refresh token");

    const tokens = issueTokens(payload.sub);
    res.json(tokens);
  } catch {
    res.status(401).json({ error: "Invalid or expired refresh token." });
  }
}
