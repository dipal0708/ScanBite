import express from "express";
import cors from "cors";
import dotenv from "dotenv";

import authRoutes from "./routes/auth.routes.js";
import profileRoutes from "./routes/profile.routes.js";
import scanRoutes from "./routes/scan.routes.js";
import { errorHandler } from "./middleware/errorHandler.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.use("/auth", authRoutes);
app.use("/profile", profileRoutes);
app.use("/scans", scanRoutes);

app.use(errorHandler);

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`LabelWise API listening on :${PORT}`);
});
