"""
CSS（OpenSearch 引擎）向量库客户端
依赖：pip install opensearch-py
鉴权：HTTP basic auth（CSS 用户名/密码，来自环境变量）
"""
import os
from opensearchpy import OpenSearch


def get_client():
    # OS_HOST 支持 "IP:PORT" 格式（CSS 内网访问地址，如 10.0.2.30:9200）；缺省端口 9200
    host_raw = os.environ["OS_HOST"]
    host, _, port_str = host_raw.partition(":")
    port = int(port_str) if port_str else 9200
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(os.environ["OS_USER"], os.environ["OS_PASSWORD"]),
        use_ssl=True,
        verify_certs=False,   # CSS 安全模式 HTTPS 自签证书；生产建议校验证书
        timeout=300,
    )


def ensure_index(client, index_name, dim):
    """创建 kNN 向量索引（如不存在）。dim 需与所选嵌入模型输出维度一致。"""
    if client.indices.exists(index=index_name):
        return
    client.indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "knn": "true",
                    "knn.algo_param.ef_search": 512,
                }
            },
            "mappings": {
                "properties": {
                    "damage_vector": {
                        "type": "knn_vector",
                        "dimension": dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                            "parameters": {"ef_construction": 128, "m": 24},
                        },
                    }
                }
            },
        },
    )
