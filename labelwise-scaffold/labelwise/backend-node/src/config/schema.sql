CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  diet_type TEXT NOT NULL,
  meat_subprefs TEXT[] DEFAULT '{}',
  health_flags TEXT[] DEFAULT '{}',
  allergens TEXT[] DEFAULT '{}',
  sugar_sensitivity NUMERIC DEFAULT 5,
  age_band TEXT,
  sex TEXT,
  activity_level TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  image_urls TEXT[] DEFAULT '{}',
  status TEXT DEFAULT 'pending',
  ocr_raw_text TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scan_results (
  scan_id UUID PRIMARY KEY REFERENCES scans(id) ON DELETE CASCADE,
  label_score NUMERIC,
  sugar_score NUMERIC,
  additive_score NUMERIC,
  diet_fit_score NUMERIC,
  flags JSONB DEFAULT '[]',
  ai_summary TEXT,
  ai_suggestions JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingredients_kb (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,
  synonyms TEXT[] DEFAULT '{}',
  category TEXT,
  e_number TEXT,
  animal_derived BOOLEAN DEFAULT false,
  root_allium BOOLEAN DEFAULT false,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS diet_rulesets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  diet_type TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  rules JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_history_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
  xp_earned INT DEFAULT 0,
  badge_unlocked TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
