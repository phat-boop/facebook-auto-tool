CREATE TABLE IF NOT EXISTS licenses (
  key_hash TEXT PRIMARY KEY,
  key_hint TEXT NOT NULL,
  hwid TEXT,
  expires_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  activated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_licenses_hwid ON licenses(hwid);
