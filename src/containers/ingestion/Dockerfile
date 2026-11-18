# 构建上下文需为仓库根目录（src/adapter 与 src/containers 同级）
# 构建示例：docker build -f src/containers/ingestion/Dockerfile -t damage-repo:ingestion .
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/containers/ingestion/requirements.txt ./requirements.txt
# 国内网络环境改用华为云 pip 镜像源（mirrors.huaweicloud.com）
RUN pip3 install -r requirements.txt --no-cache-dir -i https://mirrors.huaweicloud.com/repository/pypi/simple

COPY src/adapter /app/adapter
COPY src/containers/ingestion/image_ingestion.py /app/image_ingestion.py

RUN useradd -u 5678 --create-home appuser \
    && chown -R appuser /app

USER appuser
ENTRYPOINT ["python3", "image_ingestion.py"]
