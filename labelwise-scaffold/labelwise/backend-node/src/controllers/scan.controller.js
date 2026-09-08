import { pool } from "../config/db.js";
import { analyzeLabel, askAgentAboutScan } from "../services/aiService.js";

export async function createScan(req, res, next) {
  try {
    const images = req.files;
    if (!images || images.length === 0) {
      return res.status(400).json({ error: "Attach at least one label photo." });
    }

    const profileResult = await pool.query("SELECT * FROM profiles WHERE user_id = $1", [
      req.userId,
    ]);
    const profile = profileResult.rows[0] || null;

    // The AI service does OCR + classification + scoring + agent explanation.
    const analysis = await analyzeLabel({ images, profile });

    const scanInsert = await pool.query(
      `INSERT INTO scans (user_id, status, ocr_raw_text) VALUES ($1, 'complete', $2)
       RETURNING id, created_at`,
      [req.userId, analysis.ocrRawText]
    );
    const scan = scanInsert.rows[0];

    await pool.query(
      `INSERT INTO scan_results (
         scan_id, label_score, sugar_score, additive_score, diet_fit_score,
         flags, ai_summary, ai_suggestions
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
      [
        scan.id,
        analysis.scores.label,
        analysis.scores.sugar,
        analysis.scores.additives,
        analysis.scores.dietFit,
        JSON.stringify(analysis.flags),
        analysis.summary,
        JSON.stringify(analysis.suggestions),
      ]
    );

    // Award XP for scanning — feeds the gamified progress screen.
    await pool.query(
      `INSERT INTO scan_history_events (user_id, scan_id, xp_earned) VALUES ($1, $2, $3)`,
      [req.userId, scan.id, 10]
    );

    res.status(201).json({ scanId: scan.id, createdAt: scan.created_at, ...analysis });
  } catch (err) {
    next(err);
  }
}

export async function getScan(req, res, next) {
  try {
    const result = await pool.query(
      `SELECT s.id, s.created_at, r.*
       FROM scans s JOIN scan_results r ON r.scan_id = s.id
       WHERE s.id = $1 AND s.user_id = $2`,
      [req.params.scanId, req.userId]
    );
    if (result.rowCount === 0) return res.status(404).json({ error: "Scan not found." });
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
}

export async function askAgent(req, res, next) {
  try {
    const { question } = req.body;
    const scanResult = await pool.query(
      `SELECT r.* FROM scan_results r JOIN scans s ON s.id = r.scan_id
       WHERE r.scan_id = $1 AND s.user_id = $2`,
      [req.params.scanId, req.userId]
    );
    if (scanResult.rowCount === 0) return res.status(404).json({ error: "Scan not found." });

    const answer = await askAgentAboutScan({ scanResult: scanResult.rows[0], question });
    res.json(answer);
  } catch (err) {
    next(err);
  }
}

export async function listHistory(req, res, next) {
  try {
    const result = await pool.query(
      `SELECT s.id, s.created_at, r.label_score, r.diet_fit_score
       FROM scans s JOIN scan_results r ON r.scan_id = s.id
       WHERE s.user_id = $1 ORDER BY s.created_at DESC LIMIT 50`,
      [req.userId]
    );
    res.json(result.rows);
  } catch (err) {
    next(err);
  }
}
