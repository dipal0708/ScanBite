import { Router } from "express";
import { requireAuth } from "../middleware/auth.js";
import { getProfile, upsertProfile } from "../controllers/profile.controller.js";

const router = Router();

router.get("/", requireAuth, getProfile);
router.put("/", requireAuth, upsertProfile);

export default router;
