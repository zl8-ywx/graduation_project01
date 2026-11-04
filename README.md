# 学生管理系统

一个基于 Flask + MySQL 的学生管理系统，支持学生、班级、专业三级管理，并提供数据看板和角色权限控制。

## 功能

- 用户认证：登录、注册、退出、修改密码
- 角色权限：`admin` 管理员、`user` 普通用户
- 学生管理：增删改查、关键词搜索、按性别/班级筛选、分页
- 班级管理：班级增删改查、按专业筛选
- 专业管理：专业增删改查
- 数据看板：学生总数、性别分布、班级分布、入学年份分布
- 用户管理：管理员可查看、新增、编辑、禁用用户

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端 | Python 3.9+、Flask、PyMySQL |
| 数据库 | MySQL 8.0 |
| 前端 | Jinja2 模板、原生 HTML/CSS/JavaScript |
| 图表 | 手写 Canvas 图表，无外部 CDN 依赖 |

## 目录结构

```text
graduation_project/
├── app.py                 # 后端主程序与路由
├── config.py              # 本地数据库配置（已被 .gitignore 忽略）
├── config.example.py      # 配置模板
├── requirements.txt       # Python 依赖
├── schema.sql             # 建库建表与演示数据脚本
├── static/
│   ├── css/style.css
│   └── js/
│       ├── charts.js
│       └── main.js
└── templates/             # 页面模板
```

## 本地运行

### 1. 准备环境

- 安装 Python 3.9 及以上版本
- 安装并启动 MySQL 8.0

### 2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. 配置数据库

```powershell
Copy-Item config.example.py config.py
```

打开 `config.py`，填写本机的 MySQL 用户名、密码，并替换 `SECRET_KEY`。

### 4. 启动

```powershell
python app.py
```

程序首次启动会自动创建数据库、数据表，并在用户表为空时创建默认管理员。访问：

```text
http://127.0.0.1:5000
```

### 5. 导入演示数据（可选）

如果需要专业、班级和学生演示数据，执行：

```powershell
Get-Content .\schema.sql | mysql -uroot -p
```

### 默认账号

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | 123456 | 管理员 |
| teacher1 | 123456 | 普通用户（执行 schema.sql 后存在） |

首次登录后建议立即修改密码。

## 配置说明

`config.py` 包含数据库连接信息和会话密钥，已被 `.gitignore` 忽略，不会进入 Git 仓库。

- `DB_CONFIG`：MySQL 连接参数
- `SECRET_KEY`：Flask 会话签名密钥，部署前必须替换为随机值

生成随机密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

## 后续部署

项目计划使用 Docker、Kubernetes、Jenkins 和 Nginx 完成容器化部署与自动化运维，相关配置将在后续阶段补充。

## 安全提示

- 不要提交 `config.py`、`.env` 或任何包含密码、密钥的文件
- 不要在生产环境使用默认账号和默认密码
- 部署前必须更换 `SECRET_KEY`
