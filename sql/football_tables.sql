-- ============================================================
-- 足球 Agent 专业能力增强（Phase 1，2026-08-19）：新增球队/球员/比赛表
-- 对存量库执行（新库用 database.sql 已含）
-- 用法：mysql -uroot -p news_app < migrations/20260819_football_tables.sql
-- ============================================================
USE news_app;

-- 球队信息表
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
