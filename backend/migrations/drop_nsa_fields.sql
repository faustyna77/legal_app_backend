ALTER TABLE judgments DROP COLUMN IF EXISTS date_received;
ALTER TABLE judgments DROP COLUMN IF EXISTS judges;
ALTER TABLE judgments DROP COLUMN IF EXISTS case_category_symbol;
ALTER TABLE judgments DROP COLUMN IF EXISTS case_category_desc;
ALTER TABLE judgments DROP COLUMN IF EXISTS respondent_organ;
ALTER TABLE judgments DROP COLUMN IF EXISTS result_text;

DROP INDEX IF EXISTS idx_judgments_date_received;
DROP INDEX IF EXISTS idx_judgments_respondent_organ;
