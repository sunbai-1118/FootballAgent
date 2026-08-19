-- ============================================================
-- Agent 优化 v3.0（2026-08-19）：ai_chat 加 trace_id + 新增 answer_feedback 反馈表
-- 对存量库执行（新库用 database.sql 已含）
-- 用法：mysql -uroot -p news_app < migrations/20260819_answer_feedback.sql
-- ============================================================
USE news_app;

-- ai_chat 表补 trace_id 列（关联反馈/日志链路）
ALTER TABLE `ai_chat`
  ADD COLUMN `trace_id` VARCHAR(32) NULL DEFAULT NULL COMMENT 'OTel trace_id(关联反馈/日志链路)' AFTER `agent_trace`;

-- 回答反馈表（用户 👍/👎，用于优化 Prompt/RAG/Tool）
CREATE TABLE IF NOT EXISTS `answer_feedback` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '反馈ID',
  `ai_chat_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '关联的回答记录ID',
  `user_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '用户ID',
  `trace_id` VARCHAR(32) NULL DEFAULT NULL COMMENT 'OTel trace_id(关联日志链路)',
  `score` ENUM('up','down') NOT NULL COMMENT '反馈:up(👍)/down(👎)',
  `reason` TEXT NULL DEFAULT NULL COMMENT '反馈原因(可选)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_feedback_ai_chat` (`ai_chat_id` ASC),
  CONSTRAINT `fk_feedback_ai_chat`
    FOREIGN KEY (`ai_chat_id`)
    REFERENCES `ai_chat` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_feedback_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回答反馈表';
