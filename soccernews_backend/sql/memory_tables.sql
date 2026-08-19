-- ============================================================
-- 四层记忆架构（2026-08-17）：新增长期记忆 + 会话短期记忆表
-- 对存量库执行（新库用 database.sql 已含）
-- 用法：mysql -uroot -p news_app < migrations/20260816_memory_tables.sql
-- ============================================================
USE news_app;

-- 用户长期记忆表（经记忆筛选层入库，跨会话）
CREATE TABLE IF NOT EXISTS `user_memory` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记忆ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `content` TEXT NOT NULL COMMENT '记忆内容(用户偏好/事实)',
  `memory_type` VARCHAR(20) NOT NULL DEFAULT 'preference' COMMENT '类型:preference偏好/fact事实',
  `importance` TINYINT UNSIGNED NOT NULL DEFAULT 3 COMMENT '重要性1-5(超预算裁剪用)',
  `source_session_id` VARCHAR(64) NULL DEFAULT NULL COMMENT '来源会话',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_memory_user` (`user_id` ASC),
  CONSTRAINT `fk_user_memory_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户长期记忆(经筛选层入库)';

-- 会话短期记忆表（三层结构中的 summary + key_facts，recent_messages 存 ai_chat）
CREATE TABLE IF NOT EXISTS `session_memory` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `session_id` VARCHAR(64) NOT NULL COMMENT '会话ID',
  `summary` TEXT NULL DEFAULT NULL COMMENT '滚动摘要(早期轮次，自然语言)',
  `key_facts` TEXT NULL DEFAULT NULL COMMENT '结构化关键事实JSON',
  `summarized_upto` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '已折叠进摘要/关键事实的轮次数(从最老计)',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_session_memory` (`user_id` ASC, `session_id` ASC),
  CONSTRAINT `fk_session_memory_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话短期记忆(三层中的summary/key_facts)';
