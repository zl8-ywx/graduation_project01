# -*- coding: utf-8 -*-
"""
学生管理系统 - 后端主程序（Flask + MySQL + PyMySQL）

功能模块：
  1. 用户认证：注册 / 登录 / 退出 / 修改密码（密码哈希存储）
  2. 角色权限：admin（管理员，可管理用户）、user（普通用户）
  3. 学生管理：增删改查、关键词搜索、按性别/班级筛选、分页
  4. 班级管理：班级增删改查（每个班级隶属一个专业）
  5. 专业管理：专业增删改查
  6. 数据看板：人数统计、性别/班级/入学年份分布图表
"""
import functools
import math
import re

import pymysql
from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from config import DB_CONFIG, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 学生列表每页条数
PER_PAGE = 8

# ---------------------------------------------------------------------------
# 数据库连接
# ---------------------------------------------------------------------------

def get_db():
    """按请求复用数据库连接"""
    if "db" not in g:
        g.db = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin','user') NOT NULL DEFAULT 'user',
  status        TINYINT      NOT NULL DEFAULT 1,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS majors (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50)  NOT NULL UNIQUE,
  remark     VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS classes (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50)  NOT NULL UNIQUE,
  major_id   INT          NOT NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS students (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  stu_no      VARCHAR(20)  NOT NULL UNIQUE,
  name        VARCHAR(50)  NOT NULL,
  gender      ENUM('男','女') NOT NULL DEFAULT '男',
  class_id    INT          NOT NULL,
  phone       VARCHAR(20)  NOT NULL DEFAULT '',
  enroll_year INT          NULL,
  remark      VARCHAR(255) NOT NULL DEFAULT '',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def init_app_db():
    """程序启动时：确保数据库/数据表存在，并创建默认管理员 admin/123456"""
    cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS `{}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(DB_CONFIG["database"]))
        conn.commit()
    finally:
        conn.close()

    conn = get_raw_cursor_conn()
    try:
        with conn.cursor() as cur:
            for stmt in SCHEMA_SQL.split(";"):
                if stmt.strip():
                    cur.execute(stmt)

            # 老版本表结构迁移：students.class_name/major -> students.class_id
            cur.execute("SHOW COLUMNS FROM students LIKE 'class_name'")
            if cur.fetchone():
                cur.execute("INSERT IGNORE INTO majors (name) "
                            "SELECT DISTINCT major FROM students WHERE major <> ''")
                cur.execute("INSERT IGNORE INTO classes (name, major_id) "
                            "SELECT DISTINCT s.class_name, m.id FROM students s "
                            "JOIN majors m ON m.name = s.major "
                            "WHERE s.class_name <> ''")
                cur.execute("ALTER TABLE students ADD COLUMN class_id INT NULL AFTER gender")
                cur.execute("UPDATE students s JOIN classes c ON c.name = s.class_name "
                            "SET s.class_id = c.id")
                cur.execute("ALTER TABLE students DROP COLUMN class_name, DROP COLUMN major")

            cur.execute("SELECT COUNT(*) AS c FROM users")
            if cur.fetchone()["c"] == 0:
                cur.execute(
                    "INSERT INTO users (username, password_hash, role, status) "
                    "VALUES (%s, %s, 'admin', 1)",
                    ("admin", generate_password_hash("123456", method="pbkdf2:sha256")))
        conn.commit()
    finally:
        conn.close()


def get_raw_cursor_conn():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


# ---------------------------------------------------------------------------
# 登录态与权限控制
# ---------------------------------------------------------------------------

@app.before_request
def load_current_user():
    """每个请求前从 session 恢复当前用户"""
    g.user = None
    uid = session.get("uid")
    if not uid:
        return
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (uid,))
    u = cur.fetchone()
    if u is None or u["status"] != 1:  # 用户不存在或已被禁用
        session.clear()
    else:
        g.user = u


@app.context_processor
def inject_user():
    """把当前用户注入所有模板"""
    return {"me": g.get("user")}


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("请先登录", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("请先登录", "error")
            return redirect(url_for("login", next=request.path))
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# 认证模块：登录 / 注册 / 退出 / 修改密码
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("用户名或密码错误", "error")
        elif user["status"] != 1:
            flash("该账号已被禁用，请联系管理员", "error")
        else:
            session.clear()
            session["uid"] = user["id"]
            flash("欢迎回来，{}".format(user["username"]), "success")
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    errors = {}
    old = {"username": ""}
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        old["username"] = username

        if not re.fullmatch(r"[a-zA-Z0-9_]{3,20}", username):
            errors["username"] = "用户名需为 3-20 位字母、数字或下划线"
        if len(password) < 6:
            errors["password"] = "密码长度至少 6 位"
        if password != confirm:
            errors["confirm"] = "两次输入的密码不一致"

        if not errors:
            cur = get_db().cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                errors["username"] = "该用户名已被注册"
            else:
                cur.execute(
                    "INSERT INTO users (username, password_hash, role, status) "
                    "VALUES (%s, %s, 'user', 1)",
                    (username, generate_password_hash(password, method="pbkdf2:sha256")))
                get_db().commit()
                session.clear()
                session["uid"] = cur.lastrowid
                flash("注册成功，欢迎使用", "success")
                return redirect(url_for("dashboard"))
    return render_template("register.html", errors=errors, old=old)


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "success")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    errors = {}
    if request.method == "POST":
        old_pwd = request.form.get("old_password", "")
        new_pwd = request.form.get("new_password", "")
        confirm = request.form.get("confirm", "")

        if not check_password_hash(g.user["password_hash"], old_pwd):
            errors["old_password"] = "原密码不正确"
        if len(new_pwd) < 6:
            errors["new_password"] = "新密码长度至少 6 位"
        if new_pwd != confirm:
            errors["confirm"] = "两次输入的新密码不一致"

        if not errors:
            cur = get_db().cursor()
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                        (generate_password_hash(new_pwd, method="pbkdf2:sha256"), g.user["id"]))
            get_db().commit()
            flash("密码修改成功", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", errors=errors)


# ---------------------------------------------------------------------------
# 数据看板：统计 + 图表数据
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    cur = get_db().cursor()

    cur.execute("SELECT COUNT(*) AS c FROM students")
    total = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE gender = '男'")
    male = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM classes")
    class_count = cur.fetchone()["c"]

    cur.execute("SELECT s.stu_no, s.name, s.gender, c.name AS class_name, s.created_at "
                "FROM students s LEFT JOIN classes c ON c.id = s.class_id "
                "ORDER BY s.id DESC LIMIT 5")
    recent = []
    for r in cur.fetchall():
        r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M")
        recent.append(r)

    cur.execute("SELECT gender, COUNT(*) AS c FROM students GROUP BY gender")
    gender_data = [{"label": r["gender"], "value": r["c"]} for r in cur.fetchall()]

    cur.execute("SELECT c.name AS label, COUNT(s.id) AS value "
                "FROM classes c JOIN students s ON s.class_id = c.id "
                "GROUP BY c.id, c.name ORDER BY value DESC, c.name LIMIT 10")
    class_data = {"labels": [], "values": []}
    for r in cur.fetchall():
        class_data["labels"].append(r["label"])
        class_data["values"].append(r["value"])

    cur.execute("SELECT enroll_year AS label, COUNT(*) AS value FROM students "
                "WHERE enroll_year IS NOT NULL GROUP BY enroll_year ORDER BY label")
    year_data = {"labels": [], "values": []}
    for r in cur.fetchall():
        year_data["labels"].append(str(r["label"]))
        year_data["values"].append(r["value"])

    stats = {
        "total": total,
        "male": male,
        "female": total - male,
        "class_count": class_count,
        "recent": recent,
        "gender_data": gender_data,
        "class_data": class_data,
        "year_data": year_data,
    }
    return render_template("dashboard.html", stats=stats)


# ---------------------------------------------------------------------------
# 学生管理：列表（搜索/筛选/分页）、新增、编辑、删除、详情
# ---------------------------------------------------------------------------

def page_window(page, total_pages):
    """生成分页页码序列（超出 7 页显示省略号）"""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    pages = [1]
    for p in range(max(2, page - 2), min(total_pages - 1, page + 2) + 1):
        if isinstance(pages[-1], int) and p - pages[-1] > 1:
            pages.append("...")
        pages.append(p)
    if total_pages - pages[-1] > 1:
        pages.append("...")
    pages.append(total_pages)
    return pages


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    gender = request.args.get("gender", "").strip()
    class_id = request.args.get("class_id", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    where, params = ["1=1"], []
    if q:
        where.append("(s.stu_no LIKE %s OR s.name LIKE %s OR s.phone LIKE %s "
                     "OR m.name LIKE %s OR c.name LIKE %s)")
        like = "%{}%".format(q)
        params += [like, like, like, like, like]
    if gender in ("男", "女"):
        where.append("s.gender = %s")
        params.append(gender)
    if class_id:
        try:
            class_id = int(class_id)
        except ValueError:
            class_id = ""
        else:
            where.append("s.class_id = %s")
            params.append(class_id)
    where_sql = " AND ".join(where)

    join_sql = ("FROM students s "
                "LEFT JOIN classes c ON c.id = s.class_id "
                "LEFT JOIN majors m ON m.id = c.major_id")

    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) AS c " + join_sql + " WHERE " + where_sql, params)
    total = cur.fetchone()["c"]
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE

    cur.execute(
        "SELECT s.*, c.name AS class_name, m.name AS major " + join_sql +
        " WHERE {} ORDER BY s.id DESC LIMIT %s OFFSET %s".format(where_sql),
        params + [PER_PAGE, offset])
    rows = cur.fetchall()

    cur.execute("SELECT id, name FROM classes ORDER BY name")
    classes = cur.fetchall()

    return render_template(
        "students.html",
        rows=rows, total=total, page=page, total_pages=total_pages,
        pages=page_window(page, total_pages),
        q=q, gender=gender, class_id=class_id, classes=classes)


def validate_student(form, exclude_id=None):
    """校验学生表单，返回 (数据 dict, 错误 dict)"""
    errors = {}
    data = {
        "stu_no": form.get("stu_no", "").strip(),
        "name": form.get("name", "").strip(),
        "gender": form.get("gender", "").strip(),
        "class_id": form.get("class_id", "").strip(),
        "phone": form.get("phone", "").strip(),
        "enroll_year": form.get("enroll_year", "").strip(),
        "remark": form.get("remark", "").strip(),
    }

    if not data["stu_no"]:
        errors["stu_no"] = "学号不能为空"
    elif len(data["stu_no"]) > 20:
        errors["stu_no"] = "学号长度不能超过 20 位"
    if not data["name"]:
        errors["name"] = "姓名不能为空"
    if data["gender"] not in ("男", "女"):
        errors["gender"] = "请选择性别"
    if not data["class_id"]:
        errors["class_id"] = "请选择班级"
    else:
        try:
            cid = int(data["class_id"])
        except ValueError:
            errors["class_id"] = "请选择有效班级"
        else:
            cur = get_db().cursor()
            cur.execute("SELECT id FROM classes WHERE id = %s", (cid,))
            if cur.fetchone() is None:
                errors["class_id"] = "所选班级不存在"
            else:
                data["class_id"] = cid
    # 学号唯一性检查
    if data["stu_no"] and not errors.get("stu_no"):
        cur = get_db().cursor()
        if exclude_id is None:
            cur.execute("SELECT id FROM students WHERE stu_no = %s", (data["stu_no"],))
        else:
            cur.execute("SELECT id FROM students WHERE stu_no = %s AND id != %s",
                        (data["stu_no"], exclude_id))
        if cur.fetchone():
            errors["stu_no"] = "该学号已存在"
    if data["phone"] and not re.fullmatch(r"1[3-9]\d{9}", data["phone"]):
        errors["phone"] = "手机号格式不正确（11 位，1 开头）"
    if data["enroll_year"]:
        try:
            year = int(data["enroll_year"])
            if not 2000 <= year <= 2100:
                raise ValueError
            data["enroll_year"] = year
        except ValueError:
            errors["enroll_year"] = "入学年份格式不正确（如 2023）"
    else:
        data["enroll_year"] = None
    return data, errors


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def student_add():
    errors, old = {}, {}
    if request.method == "POST":
        old, errors = validate_student(request.form)
        if not errors:
            cur = get_db().cursor()
            cur.execute(
                "INSERT INTO students (stu_no, name, gender, class_id, phone, enroll_year, remark) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (old["stu_no"], old["name"], old["gender"], old["class_id"],
                 old["phone"], old["enroll_year"], old["remark"]))
            get_db().commit()
            flash("学生 {} 添加成功".format(old["name"]), "success")
            return redirect(url_for("students"))
    groups, class_major_map = get_class_options()
    return render_template("student_form.html", errors=errors, old=old, mode="add",
                           class_groups=groups, class_major_map=class_major_map,
                           old_major="")


@app.route("/students/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def student_edit(sid):
    cur = get_db().cursor()
    cur.execute("SELECT s.*, c.name AS class_name, m.name AS major "
                "FROM students s LEFT JOIN classes c ON c.id = s.class_id "
                "LEFT JOIN majors m ON m.id = c.major_id WHERE s.id = %s", (sid,))
    student = cur.fetchone()
    if student is None:
        abort(404)

    errors, old = {}, {k: student[k] if student[k] is not None else ""
                       for k in ("stu_no", "name", "gender", "class_id",
                                 "phone", "enroll_year", "remark")}
    if request.method == "POST":
        old, errors = validate_student(request.form, exclude_id=sid)
        if not errors:
            cur.execute(
                "UPDATE students SET stu_no=%s, name=%s, gender=%s, class_id=%s, "
                "phone=%s, enroll_year=%s, remark=%s WHERE id=%s",
                (old["stu_no"], old["name"], old["gender"], old["class_id"],
                 old["phone"], old["enroll_year"], old["remark"], sid))
            get_db().commit()
            flash("学生信息已更新", "success")
            return redirect(url_for("students"))
    groups, class_major_map = get_class_options()
    return render_template("student_form.html", errors=errors, old=old, mode="edit",
                           sid=sid, class_groups=groups, class_major_map=class_major_map,
                           old_major=student["major"] or "")


@app.route("/students/<int:sid>/delete", methods=["POST"])
@login_required
def student_delete(sid):
    cur = get_db().cursor()
    cur.execute("DELETE FROM students WHERE id = %s", (sid,))
    get_db().commit()
    flash("删除成功", "success")
    return redirect(url_for("students"))


@app.route("/students/<int:sid>")
@login_required
def student_detail(sid):
    cur = get_db().cursor()
    cur.execute("SELECT s.*, c.name AS class_name, m.name AS major "
                "FROM students s LEFT JOIN classes c ON c.id = s.class_id "
                "LEFT JOIN majors m ON m.id = c.major_id "
                "WHERE s.id = %s", (sid,))
    student = cur.fetchone()
    if student is None:
        abort(404)
    return render_template("student_detail.html", s=student)


# ---------------------------------------------------------------------------
# 班级 / 专业 通用查询
# ---------------------------------------------------------------------------

def get_class_options():
    """学生表单用：班级按专业分组 + 班级ID到专业名的映射"""
    cur = get_db().cursor()
    cur.execute(
        "SELECT c.id, c.name, m.name AS major_name "
        "FROM classes c LEFT JOIN majors m ON m.id = c.major_id "
        "ORDER BY m.name, c.name")
    groups, index, class_major_map = [], {}, {}
    for r in cur.fetchall():
        mn = r["major_name"] or "未设置专业"
        if mn not in index:
            index[mn] = len(groups)
            groups.append({"name": mn, "classes": []})
        groups[index[mn]]["classes"].append(r)
        class_major_map[str(r["id"])] = mn
    return groups, class_major_map


# ---------------------------------------------------------------------------
# 专业管理：列表、新增、编辑、删除
# ---------------------------------------------------------------------------

def validate_major(form, exclude_id=None):
    """校验专业表单，返回 (数据 dict, 错误 dict)"""
    errors = {}
    data = {
        "name": form.get("name", "").strip(),
        "remark": form.get("remark", "").strip(),
    }
    if not data["name"]:
        errors["name"] = "专业名称不能为空"
    elif len(data["name"]) > 50:
        errors["name"] = "专业名称不能超过 50 个字符"
    if data["name"] and not errors.get("name"):
        cur = get_db().cursor()
        if exclude_id is None:
            cur.execute("SELECT id FROM majors WHERE name = %s", (data["name"],))
        else:
            cur.execute("SELECT id FROM majors WHERE name = %s AND id != %s",
                        (data["name"], exclude_id))
        if cur.fetchone():
            errors["name"] = "该专业已存在"
    return data, errors


@app.route("/majors")
@login_required
def majors():
    cur = get_db().cursor()
    cur.execute(
        "SELECT m.*, (SELECT COUNT(*) FROM classes c WHERE c.major_id = m.id) AS class_count "
        "FROM majors m ORDER BY m.id")
    rows = cur.fetchall()
    return render_template("majors.html", rows=rows)


@app.route("/majors/add", methods=["GET", "POST"])
@login_required
def major_add():
    errors, old = {}, {"name": "", "remark": ""}
    if request.method == "POST":
        old, errors = validate_major(request.form)
        if not errors:
            cur = get_db().cursor()
            cur.execute("INSERT INTO majors (name, remark) VALUES (%s, %s)",
                        (old["name"], old["remark"]))
            get_db().commit()
            flash("专业「{}」添加成功".format(old["name"]), "success")
            return redirect(url_for("majors"))
    return render_template("major_form.html", errors=errors, old=old, mode="add")


@app.route("/majors/<int:mid>/edit", methods=["GET", "POST"])
@login_required
def major_edit(mid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM majors WHERE id = %s", (mid,))
    major = cur.fetchone()
    if major is None:
        abort(404)

    errors, old = {}, {"name": major["name"], "remark": major["remark"]}
    if request.method == "POST":
        old, errors = validate_major(request.form, exclude_id=mid)
        if not errors:
            cur.execute("UPDATE majors SET name=%s, remark=%s WHERE id=%s",
                        (old["name"], old["remark"], mid))
            get_db().commit()
            flash("专业信息已更新", "success")
            return redirect(url_for("majors"))
    return render_template("major_form.html", errors=errors, old=old, mode="edit", mid=mid)


@app.route("/majors/<int:mid>/delete", methods=["POST"])
@login_required
def major_delete(mid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM majors WHERE id = %s", (mid,))
    major = cur.fetchone()
    if major is None:
        abort(404)
    cur.execute("SELECT COUNT(*) AS c FROM classes WHERE major_id = %s", (mid,))
    if cur.fetchone()["c"] > 0:
        flash("专业「{}」下仍有班级，请先处理相关班级再删除".format(major["name"]), "error")
    else:
        cur.execute("DELETE FROM majors WHERE id = %s", (mid,))
        get_db().commit()
        flash("专业「{}」已删除".format(major["name"]), "success")
    return redirect(url_for("majors"))


# ---------------------------------------------------------------------------
# 班级管理：列表、新增、编辑、删除
# ---------------------------------------------------------------------------

def validate_class(form, exclude_id=None):
    """校验班级表单，返回 (数据 dict, 错误 dict)"""
    errors = {}
    data = {
        "name": form.get("name", "").strip(),
        "major_id": form.get("major_id", "").strip(),
    }
    if not data["name"]:
        errors["name"] = "班级名称不能为空"
    elif len(data["name"]) > 50:
        errors["name"] = "班级名称不能超过 50 个字符"
    if not data["major_id"]:
        errors["major_id"] = "请选择所属专业"
    else:
        try:
            mid = int(data["major_id"])
        except ValueError:
            errors["major_id"] = "请选择有效的所属专业"
        else:
            cur = get_db().cursor()
            cur.execute("SELECT id FROM majors WHERE id = %s", (mid,))
            if cur.fetchone() is None:
                errors["major_id"] = "所选专业不存在"
            else:
                data["major_id"] = mid
    if data["name"] and not errors.get("name"):
        cur = get_db().cursor()
        if exclude_id is None:
            cur.execute("SELECT id FROM classes WHERE name = %s", (data["name"],))
        else:
            cur.execute("SELECT id FROM classes WHERE name = %s AND id != %s",
                        (data["name"], exclude_id))
        if cur.fetchone():
            errors["name"] = "该班级已存在"
    return data, errors


@app.route("/classes")
@login_required
def classes():
    major_id = request.args.get("major_id", "").strip()
    if major_id:
        try:
            major_id = int(major_id)
        except ValueError:
            major_id = ""

    where = "WHERE c.major_id = %s" if major_id else ""
    params = (major_id,) if major_id else ()

    cur = get_db().cursor()
    cur.execute(
        "SELECT c.*, m.name AS major_name, "
        "(SELECT COUNT(*) FROM students s WHERE s.class_id = c.id) AS student_count "
        "FROM classes c LEFT JOIN majors m ON m.id = c.major_id "
        + where + " ORDER BY c.id", params)
    rows = cur.fetchall()
    cur.execute("SELECT id, name FROM majors ORDER BY id")
    majors_all = cur.fetchall()
    return render_template("classes.html", rows=rows, major_id=major_id, majors_all=majors_all)


@app.route("/classes/add", methods=["GET", "POST"])
@login_required
def class_add():
    errors, old = {}, {"name": "", "major_id": ""}
    if request.method == "POST":
        old, errors = validate_class(request.form)
        if not errors:
            cur = get_db().cursor()
            cur.execute("INSERT INTO classes (name, major_id) VALUES (%s, %s)",
                        (old["name"], old["major_id"]))
            get_db().commit()
            flash("班级「{}」添加成功".format(old["name"]), "success")
            return redirect(url_for("classes"))
    cur = get_db().cursor()
    cur.execute("SELECT id, name FROM majors ORDER BY id")
    return render_template("class_form.html", errors=errors, old=old, mode="add",
                           majors_all=cur.fetchall())


@app.route("/classes/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def class_edit(cid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM classes WHERE id = %s", (cid,))
    cls = cur.fetchone()
    if cls is None:
        abort(404)

    errors, old = {}, {"name": cls["name"], "major_id": cls["major_id"]}
    if request.method == "POST":
        old, errors = validate_class(request.form, exclude_id=cid)
        if not errors:
            cur.execute("UPDATE classes SET name=%s, major_id=%s WHERE id=%s",
                        (old["name"], old["major_id"], cid))
            get_db().commit()
            flash("班级信息已更新", "success")
            return redirect(url_for("classes"))
    cur.execute("SELECT id, name FROM majors ORDER BY id")
    return render_template("class_form.html", errors=errors, old=old, mode="edit",
                           cid=cid, majors_all=cur.fetchall())


@app.route("/classes/<int:cid>/delete", methods=["POST"])
@login_required
def class_delete(cid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM classes WHERE id = %s", (cid,))
    cls = cur.fetchone()
    if cls is None:
        abort(404)
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE class_id = %s", (cid,))
    if cur.fetchone()["c"] > 0:
        flash("班级「{}」下仍有学生，请先处理相关学生再删除".format(cls["name"]), "error")
    else:
        cur.execute("DELETE FROM classes WHERE id = %s", (cid,))
        get_db().commit()
        flash("班级「{}」已删除".format(cls["name"]), "success")
    return redirect(url_for("classes"))


# ---------------------------------------------------------------------------
# 用户管理（仅管理员）
# ---------------------------------------------------------------------------

@app.route("/users")
@admin_required
def users():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users ORDER BY id")
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin' AND status = 1")
    active_admin = cur.fetchone()["c"]
    return render_template("users.html", rows=rows, active_admin=active_admin)


@app.route("/users/add", methods=["GET", "POST"])
@admin_required
def user_add():
    errors, old = {}, {"username": "", "role": "user"}
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        old = {"username": username, "role": role if role in ("admin", "user") else "user"}

        if not re.fullmatch(r"[a-zA-Z0-9_]{3,20}", username):
            errors["username"] = "用户名需为 3-20 位字母、数字或下划线"
        if len(password) < 6:
            errors["password"] = "密码长度至少 6 位"
        if role not in ("admin", "user"):
            errors["role"] = "角色不合法"
        if not errors:
            cur = get_db().cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                errors["username"] = "该用户名已存在"
            else:
                cur.execute(
                    "INSERT INTO users (username, password_hash, role, status) "
                    "VALUES (%s, %s, %s, 1)",
                    (username, generate_password_hash(password, method="pbkdf2:sha256"), role))
                get_db().commit()
                flash("用户 {} 创建成功".format(username), "success")
                return redirect(url_for("users"))
    return render_template("user_form.html", errors=errors, old=old)


@app.route("/users/<int:uid>/toggle", methods=["POST"])
@admin_required
def user_toggle(uid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (uid,))
    target = cur.fetchone()
    if target is None:
        abort(404)
    if uid == g.user["id"]:
        flash("不能禁用自己的账号", "error")
    elif target["role"] == "admin" and target["status"] == 1:
        flash("不能禁用处于启用状态的管理员账号", "error")
    else:
        cur.execute("UPDATE users SET status = %s WHERE id = %s",
                    (0 if target["status"] == 1 else 1, uid))
        get_db().commit()
        flash("已{}账号 {}".format("禁用" if target["status"] == 1 else "启用", target["username"]), "success")
    return redirect(url_for("users"))


@app.route("/users/<int:uid>/delete", methods=["POST"])
@admin_required
def user_delete(uid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (uid,))
    target = cur.fetchone()
    if target is None:
        abort(404)
    if uid == g.user["id"]:
        flash("不能删除自己的账号", "error")
    elif target["role"] == "admin":
        # 数据库中至少保留一名管理员
        cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'")
        if cur.fetchone()["c"] <= 1:
            flash("系统至少保留一名管理员，无法删除", "error")
        else:
            cur.execute("DELETE FROM users WHERE id = %s", (uid,))
            get_db().commit()
            flash("用户 {} 已删除".format(target["username"]), "success")
    else:
        cur.execute("DELETE FROM users WHERE id = %s", (uid,))
        get_db().commit()
        flash("用户 {} 已删除".format(target["username"]), "success")
    return redirect(url_for("users"))


# ---------------------------------------------------------------------------
# 错误页
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, msg="没有权限访问该页面"), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, msg="页面不存在或数据已被删除"), 404


if __name__ == "__main__":
    init_app_db()
    app.run(host="127.0.0.1", port=5000, debug=True)