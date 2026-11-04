# -*- coding: utf-8 -*-
"""配置模板：复制为 config.py 后，按本机环境填写。

PowerShell 下复制命令：
    Copy-Item config.example.py config.py

注意：config.py 已加入 .gitignore，不要提交到仓库。
"""

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "CHANGE_ME",
    "database": "student_manage",
    "charset": "utf8mb4",
}

# 生产环境请替换为随机长字符串，可用下面的命令生成：
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = "CHANGE_ME_TO_A_RANDOM_STRING"
