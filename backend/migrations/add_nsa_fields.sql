ALTER TABLE judgments ADD COLUMN IF NOT EXISTS date_received DATE;
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS judges TEXT[];
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS case_category_symbol VARCHAR(100);
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS case_category_desc TEXT;
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS respondent_organ TEXT;
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS result_text TEXT;

CREATE INDEX IF NOT EXISTS idx_judgments_date_received ON judgments(date_received);
CREATE INDEX IF NOT EXISTS idx_judgments_respondent_organ ON judgments(respondent_organ);
