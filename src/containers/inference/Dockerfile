# 构建上下文需为仓库根目录
# 构建示例：docker build -f src/containers/inference/Dockerfile -t damage-repo:inference .
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/containers/inference/requirements.txt ./requirements.txt
# 国内网络环境改用华为云 pip 镜像源（mirrors.huaweicloud.com）
RUN pip3 install -r requirements.txt --no-cache-dir -i https://mirrors.huaweicloud.com/repository/pypi/simple

COPY src/adapter /app/adapter
COPY src/containers/inference/inference_ui.py /app/inference_ui.py

EXPOSE 8501

RUN useradd -u 5678 --create-home appuser \
    && chown -R appuser /app

USER appuser
ENTRYPOINT ["streamlit", "run", "inference_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
