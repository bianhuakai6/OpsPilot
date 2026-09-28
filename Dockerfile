FROM python:3.13-slim

ARG APP_VERSION=dev
ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="OpsPilot" \
      org.opencontainers.image.description="Local-first application delivery and intelligent operations platform" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPSPILOT_HOST=0.0.0.0 \
    OPSPILOT_PORT=8000

WORKDIR /app

# 生产镜像只安装运行依赖，测试仍在宿主机或 CI 中执行。
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.34.0" \
    SQLAlchemy==2.0.36 \
    PyMySQL==1.1.1 \
    cryptography==50.0.1 \
    redis==5.2.1 \
    prometheus-client==0.21.1

COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
