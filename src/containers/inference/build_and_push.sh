#!/usr/bin/env bash
# 构建并推送 inference 镜像到华为云 SWR（软件仓库）
# 用法：./build_and_push.sh <region> <project> <image> <tag>
set -euo pipefail

REGION="${1:-cn-north-4}"
PROJECT="${2:-<your-project>}"
IMAGE="${3:-damage-repo}"
TAG="${4:-inference}"

SWR_HOST="swr.${REGION}.myhuaweicloud.com"
SWR_REPO="${SWR_HOST}/${PROJECT}/${IMAGE}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "[*] SWR 登录"
docker login -u "${HW_ACCESS_KEY}" -p "${SWR_LOGIN_PASSWORD}" "${SWR_HOST}"

echo "[*] 构建镜像（上下文=${REPO_ROOT}）"
docker build -f "${REPO_ROOT}/src/containers/inference/Dockerfile" -t "${IMAGE}:${TAG}" "${REPO_ROOT}"

echo "[*] 打标签并推送"
docker tag "${IMAGE}:${TAG}" "${SWR_REPO}:${TAG}"
docker push "${SWR_REPO}:${TAG}"
echo "[+] 推送完成：${SWR_REPO}:${TAG}"
