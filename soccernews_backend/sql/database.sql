-- 新闻资讯应用数据库设计
-- 创建数据库
CREATE DATABASE IF NOT EXISTS news_app DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE news_app;

-- 用户表
CREATE TABLE IF NOT EXISTS `user` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
  `nickname` VARCHAR(50) NULL DEFAULT NULL COMMENT '昵称',
  `avatar` VARCHAR(255) NULL DEFAULT NULL COMMENT '头像URL',
  `gender` ENUM('male', 'female', 'unknown') NULL DEFAULT 'unknown' COMMENT '性别',
  `bio` VARCHAR(500) NULL DEFAULT NULL COMMENT '个人简介',
  `phone` VARCHAR(20) NULL DEFAULT NULL COMMENT '手机号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `username_UNIQUE` (`username` ASC),
  UNIQUE INDEX `phone_UNIQUE` (`phone` ASC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- 用户令牌表
CREATE TABLE IF NOT EXISTS `user_token` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '令牌ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `token` VARCHAR(255) NOT NULL COMMENT '令牌值',
  `expires_at` TIMESTAMP NOT NULL COMMENT '过期时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `token_UNIQUE` (`token` ASC),
  INDEX `fk_user_token_user_idx` (`user_id` ASC),
  CONSTRAINT `fk_user_token_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户令牌表';

-- 新闻分类表
CREATE TABLE IF NOT EXISTS `news_category` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` VARCHAR(50) NOT NULL COMMENT '分类名称',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序顺序',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_UNIQUE` (`name` ASC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻分类表';

-- 新闻表
CREATE TABLE IF NOT EXISTS `news` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '新闻ID',
  `title` VARCHAR(255) NOT NULL COMMENT '新闻标题',
  `description` VARCHAR(500) NULL DEFAULT NULL COMMENT '新闻简介',
  `content` TEXT NOT NULL COMMENT '新闻内容',
  `image` VARCHAR(255) NULL DEFAULT NULL COMMENT '封面图片URL',
  `author` VARCHAR(50) NULL DEFAULT NULL COMMENT '作者',
  `category_id` INT UNSIGNED NOT NULL COMMENT '分类ID',
  `views` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '浏览量',
  `publish_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `fk_news_category_idx` (`category_id` ASC),
  INDEX `idx_publish_time` (`publish_time` DESC),
  CONSTRAINT `fk_news_category`
    FOREIGN KEY (`category_id`)
    REFERENCES `news_category` (`id`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻表';

-- 相关新闻关联表（推荐系统）
CREATE TABLE IF NOT EXISTS `related_news` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `news_id` INT UNSIGNED NOT NULL COMMENT '新闻ID',
  `related_news_id` INT UNSIGNED NOT NULL COMMENT '相关新闻ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `news_related_unique` (`news_id` ASC, `related_news_id` ASC),
  INDEX `fk_related_news_news_idx` (`news_id` ASC),
  INDEX `fk_related_news_related_idx` (`related_news_id` ASC),
  CONSTRAINT `fk_related_news_news`
    FOREIGN KEY (`news_id`)
    REFERENCES `news` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_related_news_related`
    FOREIGN KEY (`related_news_id`)
    REFERENCES `news` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='相关新闻关联表';

-- 收藏表
CREATE TABLE IF NOT EXISTS `favorite` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '收藏ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `news_id` INT UNSIGNED NOT NULL COMMENT '新闻ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `user_news_unique` (`user_id` ASC, `news_id` ASC),
  INDEX `fk_favorite_user_idx` (`user_id` ASC),
  INDEX `fk_favorite_news_idx` (`news_id` ASC),
  CONSTRAINT `fk_favorite_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_favorite_news`
    FOREIGN KEY (`news_id`)
    REFERENCES `news` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收藏表';

-- 浏览历史表
CREATE TABLE IF NOT EXISTS `history` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '历史ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `news_id` INT UNSIGNED NOT NULL COMMENT '新闻ID',
  `view_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '浏览时间',
  PRIMARY KEY (`id`),
  INDEX `fk_history_user_idx` (`user_id` ASC),
  INDEX `fk_history_news_idx` (`news_id` ASC),
  INDEX `idx_view_time` (`view_time` DESC),
  UNIQUE INDEX `user_news_unique` (`user_id` ASC, `news_id` ASC),
  CONSTRAINT `fk_history_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_history_news`
    FOREIGN KEY (`news_id`)
    REFERENCES `news` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='浏览历史表';

-- AI聊天记录表（Agent）
CREATE TABLE IF NOT EXISTS `ai_chat` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '聊天记录ID',
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `session_id` VARCHAR(64) NULL DEFAULT NULL COMMENT '会话ID',
  `message` TEXT NOT NULL COMMENT '用户消息',
  `response` TEXT NOT NULL COMMENT 'AI回复',
  `agent_trace` TEXT NULL DEFAULT NULL COMMENT 'Agent工具调用轨迹JSON',
  `trace_id` VARCHAR(32) NULL DEFAULT NULL COMMENT 'OTel trace_id(关联反馈/日志链路)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `fk_ai_chat_user_idx` (`user_id` ASC),
  INDEX `idx_ai_chat_session` (`user_id` ASC, `session_id` ASC),
  INDEX `idx_created_at` (`created_at` DESC),
  CONSTRAINT `fk_ai_chat_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI聊天记录表';

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

-- 球队信息表（Phase 1 足球专业 Agent）
CREATE TABLE IF NOT EXISTS `team` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '球队ID',
  `name` VARCHAR(100) NOT NULL COMMENT '球队名',
  `country` VARCHAR(50) NULL DEFAULT NULL COMMENT '国家',
  `league` VARCHAR(50) NULL DEFAULT NULL COMMENT '所属联赛',
  `logo_url` VARCHAR(255) NULL DEFAULT NULL COMMENT '队徽URL',
  `api_id` INT UNSIGNED NULL DEFAULT NULL COMMENT 'api-football外部ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_team_api_id` (`api_id` ASC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球队信息表';

-- 球员信息表
CREATE TABLE IF NOT EXISTS `player` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '球员ID',
  `team_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '所属球队',
  `name` VARCHAR(100) NOT NULL COMMENT '球员名',
  `position` VARCHAR(50) NULL DEFAULT NULL COMMENT '位置',
  `nationality` VARCHAR(50) NULL DEFAULT NULL COMMENT '国籍',
  `age` INT UNSIGNED NULL DEFAULT NULL COMMENT '年龄',
  `photo_url` VARCHAR(255) NULL DEFAULT NULL COMMENT '照片URL',
  `api_id` INT UNSIGNED NULL DEFAULT NULL COMMENT 'api-football外部ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_player_team` (`team_id` ASC),
  UNIQUE INDEX `uk_player_api_id` (`api_id` ASC),
  CONSTRAINT `fk_player_team`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球员信息表';

-- 比赛信息表（MATCH 为 MySQL 保留字，建表/查询需带反引号）
CREATE TABLE IF NOT EXISTS `match` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '比赛ID',
  `league` VARCHAR(50) NULL DEFAULT NULL COMMENT '联赛',
  `season` VARCHAR(10) NULL DEFAULT NULL COMMENT '赛季',
  `round` VARCHAR(50) NULL DEFAULT NULL COMMENT '轮次/阶段',
  `home_team_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '主队ID',
  `away_team_id` INT UNSIGNED NULL DEFAULT NULL COMMENT '客队ID',
  `home_team` VARCHAR(100) NOT NULL COMMENT '主队名(冗余便于展示)',
  `away_team` VARCHAR(100) NOT NULL COMMENT '客队名(冗余便于展示)',
  `match_date` DATETIME NULL DEFAULT NULL COMMENT '比赛时间',
  `status` VARCHAR(20) NULL DEFAULT NULL COMMENT '状态:scheduled/live/finished',
  `home_score` INT UNSIGNED NULL DEFAULT NULL COMMENT '主队比分',
  `away_score` INT UNSIGNED NULL DEFAULT NULL COMMENT '客队比分',
  `venue` VARCHAR(100) NULL DEFAULT NULL COMMENT '场地',
  `api_id` INT UNSIGNED NULL DEFAULT NULL COMMENT 'api-football fixture外部ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_match_home` (`home_team_id` ASC),
  INDEX `idx_match_away` (`away_team_id` ASC),
  UNIQUE INDEX `uk_match_api_id` (`api_id` ASC),
  CONSTRAINT `fk_match_home_team`
    FOREIGN KEY (`home_team_id`)
    REFERENCES `team` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_match_away_team`
    FOREIGN KEY (`away_team_id`)
    REFERENCES `team` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='比赛信息表';

-- 初始化数据
-- 插入默认新闻分类
INSERT INTO `news_category` (`name`, `sort_order`) VALUES
('英超', 1),
('西甲', 2),
('意甲', 3),
('德甲', 4),
('法甲', 5),
('中超', 6),
('欧冠', 7),
('世界杯', 8);

-- 创建测试用户
INSERT INTO `user` (`username`, `password`, `nickname`, `gender`, `bio`) VALUES 
('admin', '$2b$12$TKevPbXcGL6Q1WdaFKbLhuueBuLfLyhkdk/0ESBvBv7X74.rNwiNm', '测试用户', 'unknown', '这是一个测试账号');