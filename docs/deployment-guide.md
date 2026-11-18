# 部署指导 — automotive-damage-processing

> 完整命令级步骤。阅读前请先了解 `docs/architecture.md`。

## 0. 前置条件

| 项目 | 要求 |
|------|------|
| 账号 | 华为云账号，具备 VPC / ELB / CCE / CSS / OBS / SWR / IAM / LTS / ModelArts 创建权限 |
| 工具 | Terraform ≥ 1.5（huaweicloud provider 1.96.0）、kubectl、docker、华为云 CLI（可选） |
| 区域 | 默认 `cn-north-4`；切换区域需同步改 `variables.tf` 的 `region` 与各镜像仓库域名 |
| 模型 | 在 **ModelArts Studio（MaaS）** 开通对话模型（如 `pangu-nlp-2024-12`）与文本嵌入模型（如 `pangu-embedding-v1`），并获取 API Key |

## 1. 准备凭据

按下列来源准备凭据；推荐用环境变量临时持有，不写入任何文件：

| 变量 | 来源 | 说明 |
|------|------|------|
| `HW_ACCESS_KEY` / `HW_SECRET_KEY` | 华为云控制台 → 「我的凭证」 → Access Key | Terraform 调华为云 API 用 |
| `HW_REGION_NAME` | 目标区域标识 | 默认 `cn-north-4` |
| `MAAS_API_KEY` | ModelArts Studio（MaaS）服务凭证 | 推理 / 嵌入调用 |
| `SWR_LOGIN_PASSWORD` | SWR 登录密码 | 镜像推送 |

```bash
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"
export HW_REGION_NAME="cn-north-4"
export MAAS_API_KEY="<MAAS-API-KEY>"
export SWR_LOGIN_PASSWORD="<SWR-LOGIN-PASSWORD>"
```

> 本地离线 `validate` / `plan` 时如需自定义 provider 镜像，可在 `infra/dev.rc` 用 `dev_overrides` 指向本地镜像；正式环境按标准 provider 安装流程，无需此文件。

## 2. 基础设施（Terraform）

```bash
cd infra
terraform init -input=false
terraform plan -out=tfplan          # 仔细检查 Resources 数与规格
terraform apply tfplan              # ⚠️ apply 前请先确认 plan 资源清单
```

`terraform output` 会给出后续所需值：

| 输出 | 用途 |
|------|------|
| `obs_frontend_bucket` / `obs_source_bucket` | 填入 k8s ConfigMap 的 `OBS_BUCKET` / `OBS_BUCKET_SOURCE` |
| `css_os_host` | 填入 ConfigMap 的 `OS_HOST`（不含 `https://`） |
| `elb_id` | 填入 inference Service 注解 `kubernetes.io/elb.id` |
| `elb_eip` | 推理 UI 公网访问地址（HTTP:80） |
| `cce_kubeconfig` | `kubectl` 连接用，敏感，勿提交 |

## 3. 构建并推送镜像到 SWR

```bash
# inference
cd src/containers/inference && ./build_and_push.sh cn-north-4 <your-project> damage-repo inference
# ingestion
cd src/containers/ingestion && ./build_and_push.sh cn-north-4 <your-project> damage-repo ingestion
```

推送后把 `src/containers/inference/k8s/deployment.yaml` 与 `ingestion/k8s/job.yaml` 中的镜像地址 `<your-project>` 替换为实际 SWR 组织名。

## 4. 填写 k8s 清单占位符

- `configmap.yaml`：`OS_HOST`、`OBS_BUCKET`、`OBS_BUCKET_SOURCE`、`APP_BASE_URL`、`CHAT_MODEL`、`EMBEDDING_MODEL`、`EMBEDDING_DIM`（须与嵌入模型输出维度一致）。
- `secret.yaml`：用命令创建真实 Secret（见文件头部注释），**不要**把明文写回 yaml：
  ```bash
  kubectl create secret generic damage-secret \
    --from-literal=HW_ACCESS_KEY=<AK> \
    --from-literal=HW_SECRET_KEY=<SK> \
    --from-literal=MAAS_API_KEY=<MAAS-API-KEY> \
    --from-literal=OS_USER=admin \
    --from-literal=OS_PASSWORD=<css-password>
  ```
- `service.yaml`：把 `<ELB_ID>` 替换为 `terraform output elb_id` 的值。

## 5. 部署工作负载

```bash
kubectl apply -f src/containers/inference/k8s/configmap.yaml
kubectl apply -f src/containers/inference/k8s/secret.yaml
kubectl apply -f src/containers/inference/k8s/deployment.yaml
kubectl apply -f src/containers/inference/k8s/service.yaml
kubectl apply -f src/containers/ingestion/k8s/job.yaml   # 灌库（一次性）
kubectl get pods,svc,job
```

## 6. 灌库与验证

1. 上传损伤源图到 OBS `source` 桶的 `repair-data/` 前缀（或用 `obsutil cp`）。
2. 观察 ingestion Job 完成（`kubectl get job damage-ingestion` → COMPLETIONS 1/1）。
3. 浏览器访问 `http://<elb_eip>`，上传一张损伤图、选参数，应返回 Top-K 匹配图与估价说明。

## 7. 清理资源

```bash
kubectl delete -f src/containers/ingestion/k8s/job.yaml
kubectl delete -f src/containers/inference/k8s/service.yaml
kubectl delete -f src/containers/inference/k8s/deployment.yaml
kubectl delete -f src/containers/inference/k8s/secret.yaml
kubectl delete -f src/containers/inference/k8s/configmap.yaml
cd infra && terraform destroy -input=false   # 释放全部云资源
# 另需手动清空 OBS 两桶后销毁（force_destroy=true 已开启可自动清）
```
