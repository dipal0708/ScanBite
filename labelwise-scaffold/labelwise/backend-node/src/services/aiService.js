import axios from "axios";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: AI_SERVICE_URL, timeout: 30_000 });

/**
 * Sends label images + the user's diet/health profile to the Python AI
 * service and gets back structured analysis (this call does OCR,
 * ingredient classification, scoring, diet-fit checking, and the
 * AI agent's plain-language explanation in one round trip).
 */
export async function analyzeLabel({ images, profile }) {
  const form = new FormData();
  images.forEach((file, i) => {
    form.append("images", new Blob([file.buffer], { type: file.mimetype }), `label_${i}.jpg`);
  });
  form.append("profile", JSON.stringify(profile || {}));

  const { data } = await client.post("/analyze", form);
  return data;
}

/** Follow-up question to the AI agent about a specific past scan result. */
export async function askAgentAboutScan({ scanResult, question }) {
  const { data } = await client.post("/agent/ask", { scanResult, question });
  return data;
}
