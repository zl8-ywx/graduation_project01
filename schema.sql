-- ============================================================
-- 学生管理系统 数据库初始化脚本（MySQL 5.7+ / 8.0）
-- 用法：mysql -uroot -p < schema.sql
-- 说明：程序启动时也会自动建表并创建默认管理员，本脚本用于
--        手动导入，并附带演示数据和默认账号。
-- 默认账号：admin / 123456 （管理员）、teacher1 / 123456 （普通用户）
-- ============================================================

CREATE DATABASE IF NOT EXISTS student_manage
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE student_manage;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE COMMENT '登录用户名',
  password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
  role          ENUM('admin','user') NOT NULL DEFAULT 'user' COMMENT '角色',
  status        TINYINT      NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户';

-- 专业表
CREATE TABLE IF NOT EXISTS majors (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50)  NOT NULL UNIQUE COMMENT '专业名称',
  remark     VARCHAR(255) NOT NULL DEFAULT '' COMMENT '备注',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业';

-- 班级表
CREATE TABLE IF NOT EXISTS classes (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50)  NOT NULL UNIQUE COMMENT '班级名称',
  major_id   INT          NOT NULL COMMENT '所属专业ID（majors.id）',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级';

-- 学生表
CREATE TABLE IF NOT EXISTS students (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  stu_no      VARCHAR(20)  NOT NULL UNIQUE COMMENT '学号',
  name        VARCHAR(50)  NOT NULL COMMENT '姓名',
  gender      ENUM('男','女') NOT NULL DEFAULT '男' COMMENT '性别',
  class_id    INT          NOT NULL COMMENT '所属班级ID（classes.id）',
  phone       VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '手机号',
  enroll_year INT          NULL COMMENT '入学年份',
  remark      VARCHAR(255) NOT NULL DEFAULT '' COMMENT '备注',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生信息';

-- 默认用户（密码均为 123456）
INSERT IGNORE INTO users (username, password_hash, role, status) VALUES
('admin',    'pbkdf2:sha256:1000000$8OoWHSYGz23zETiz$5a7ad370282155e7fbe1dc2129a8edc14786759e51cde8d0f1a3a12b8b0cad08', 'admin', 1),
('teacher1', 'pbkdf2:sha256:1000000$NlOiHeW4zxWrhqB5$555c6dfa151a6c3a5605c8c4680f3f75e39cbd2f18ac369f7dfd5d71329db415', 'user',  1);

-- 演示专业
INSERT IGNORE INTO majors (name) VALUES
('软件工程'), ('计算机科学与技术'), ('人工智能'), ('网络工程');

-- 演示班级
INSERT IGNORE INTO classes (name, major_id) VALUES
('软件开发231', (SELECT id FROM majors WHERE name = '软件工程')),
('软件开发232', (SELECT id FROM majors WHERE name = '计算机科学与技术')),
('人工智能231', (SELECT id FROM majors WHERE name = '人工智能')),
('网络工程231', (SELECT id FROM majors WHERE name = '网络工程')),
('软件开发241', (SELECT id FROM majors WHERE name = '软件工程'));

-- 演示学生数据
INSERT IGNORE INTO students
(stu_no, name, gender, class_id, phone, enroll_year, remark) VALUES
('20230101', '张伟', '男', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340001', 2023, '班长'),
('20230102', '王芳', '女', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340002', 2023, ''),
('20230103', '李娜', '女', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340003', 2023, ''),
('20230104', '刘洋', '男', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340004', 2023, ''),
('20230105', '陈静', '女', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340005', 2023, ''),
('20230106', '杨帆', '男', (SELECT id FROM classes WHERE name = '软件开发231'), '13812340006', 2023, ''),
('20230201', '赵磊', '男', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340007', 2023, ''),
('20230202', '黄敏', '女', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340008', 2023, ''),
('20230203', '周杰', '男', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340009', 2023, ''),
('20230204', '吴桐', '女', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340010', 2023, ''),
('20230205', '徐婷', '女', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340011', 2023, ''),
('20230206', '孙浩', '男', (SELECT id FROM classes WHERE name = '软件开发232'), '13812340012', 2023, ''),
('20230301', '马丽', '女', (SELECT id FROM classes WHERE name = '人工智能231'), '13812340013', 2023, ''),
('20230302', '朱军', '男', (SELECT id FROM classes WHERE name = '人工智能231'), '13812340014', 2023, ''),
('20230303', '胡雪', '女', (SELECT id FROM classes WHERE name = '人工智能231'), '13812340015', 2023, ''),
('20230304', '郭强', '男', (SELECT id FROM classes WHERE name = '人工智能231'), '13812340016', 2023, ''),
('20230305', '何静', '女', (SELECT id FROM classes WHERE name = '人工智能231'), '13812340017', 2023, ''),
('20230401', '高翔', '男', (SELECT id FROM classes WHERE name = '网络工程231'), '13812340018', 2023, ''),
('20230402', '林悦', '女', (SELECT id FROM classes WHERE name = '网络工程231'), '13812340019', 2023, ''),
('20230403', '罗成', '男', (SELECT id FROM classes WHERE name = '网络工程231'), '13812340020', 2023, ''),
('20230404', '郑爽', '女', (SELECT id FROM classes WHERE name = '网络工程231'), '13812340021', 2023, ''),
('20240101', '梁博', '男', (SELECT id FROM classes WHERE name = '软件开发241'), '13812340022', 2024, ''),
('20240102', '谢雨', '女', (SELECT id FROM classes WHERE name = '软件开发241'), '13812340023', 2024, ''),
('20240103', '韩冰', '男', (SELECT id FROM classes WHERE name = '软件开发241'), '13812340024', 2024, '');