ALTER TABLE judgments ADD COLUMN IF NOT EXISTS judgment_type VARCHAR(50);
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS is_final VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_judgments_judgment_type ON judgments(judgment_type);
CREATE INDEX IF NOT EXISTS idx_judgments_is_final ON judgments(is_final);

ALTER TABLE judgments ADD COLUMN IF NOT EXISTS content_updated_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_judgments_content_updated_at ON judgments(content_updated_at DESC) WHERE content_updated_at IS NOT NULL;
