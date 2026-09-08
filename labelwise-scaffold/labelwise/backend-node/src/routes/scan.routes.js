import { Router } from "express";
import multer from "multer";
import { requireAuth } from "../middleware/auth.js";
import { createScan, getScan, askAgent, listHistory } from "../controllers/scan.controller.js";

const router = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 8 * 1024 * 1024 } });

router.post("/", requireAuth, upload.array("images", 3), createScan);
router.get("/:scanId", requireAuth, getScan);
router.post("/:scanId/ask", requireAuth, askAgent);
router.get("/", requireAuth, listHistory);

export default router;
