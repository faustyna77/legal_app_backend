-- Migration: add folder_id to user_chat_history, make judgment_id nullable, drop search history

ALTER TABLE user_chat_history
    ADD COLUMN IF NOT EXISTS folder_id INTEGER REFERENCES user_folders(id) ON DELETE CASCADE;

ALTER TABLE user_chat_history
    ALTER COLUMN judgment_id DROP NOT NULL;

ALTER TABLE user_chat_history
    ADD COLUMN IF NOT EXISTS folder_name VARCHAR(255);

DROP TABLE IF EXISTS user_search_history;

CREATE INDEX IF NOT EXISTS idx_user_chat_history_folder ON user_chat_history(folder_id);
