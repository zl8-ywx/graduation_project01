# ============================================================
# 学生管理系统 - 容器镜像（CI/CD 平台示例应用）
# 构建：docker build -t student-manage/app:<tag> .
# 运行：docker run -p 5000:5000 \
#         -e DB_HOST=mysql -e DB_USER=root -e DB_PASSWORD=xxx \
#         -e DB_NAME=student_manage -e SECRET_KEY=xxx \
#         student-manage/app:<tag>
# ============================================================
FROM python:3.11-slim

# 关闭字节码缓存、开启 stdout 实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先装依赖，利用镜像层缓存：代码变更时依赖层不重建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝应用代码
COPY . .

# 创建非 root 用户运行应用
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# 容器健康检查（docker compose 用；K8s 中由探针配置接管）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz').status==200 else 1)"

# gunicorn 启动：2 worker + 2 线程，适配小规格虚拟机
CMD ["gunicorn", "--bind", "0.0.0.0:5000",
     "--workers", "2", "--threads", "2",
     "--access-logfile", "-", "app:app"]
