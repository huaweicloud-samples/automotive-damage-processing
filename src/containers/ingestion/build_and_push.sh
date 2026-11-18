#!/usr/bin/env bash
# 构建并推送 ingestion 镜像到华为云 SWR（软件仓库）
# 前置：已安装 docker；已获取 SWR 登录指令（控制台「容器镜像服务 → 我的镜像 → 右上角登录指令」）
# 用法：./build_and_push.sh <region> <project> <image> <tag>
#   region  例 cn-north-4
#   project 例 <your-project>   (SWR 组织/项目名)
#   image   例 damage-repo
#   tag     例 ingestion
set -euo pipefail

REGION="${1:-cn-north-4}"
PROJECT="${2:-<your-project>}"
IMAGE="${3:-damage-repo}"
TAG="${4:-ingestion}"

SWR_HOST="swr.${REGION}.myhuaweicloud.com"
SWR_REPO="${SWR_HOST}/${PROJECT}/${IMAGE}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "[*] SWR 登录（请用控制台获取的 SWR 登录密码 / 临时 token 作为密码）"
docker login -u "${HW_ACCESS_KEY}" -p "${SWR_LOGIN_PASSWORD}" "${SWR_HOST}"

echo "[*] 构建镜像（上下文=${REPO_ROOT}）"
docker build -f "${REPO_ROOT}/src/containers/ingestion/Dockerfile" -t "${IMAGE}:${TAG}" "${REPO_ROOT}"

echo "[*] 打标签并推送"
docker tag "${IMAGE}:${TAG}" "${SWR_REPO}:${TAG}"
docker push "${SWR_REPO}:${TAG}"
echo "[+] 推送完成：${SWR_REPO}:${TAG}"
