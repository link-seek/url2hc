# url2hc

URL/镜像中转到华为云（OBS + SWR）。全部硬编码均已参数化，默认值保持向后兼容。

## 用法 - 文件下载到 OBS

```bash
gh workflow run download-to-obs.yml --repo link-seek/url2hc \
  -f url="https://example.com/file.tar.gz" \
  -f obs_key="file.tar.gz"
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | 是 | - | 下载地址 |
| `obs_key` | 否 | `<文件名>` | `<prefix>` 下的相对路径 |
| `bucket` | 否 | `xieyucheng` | OBS 桶名 |
| `region` | 否 | `cn-north-9` | OBS 区域 |
| `prefix` | 否 | `下载/` | OBS key 前缀（空=桶根） |
| `expire_days` | 否 | `7` | 自动删除+签名天数（`<=0` 永久保留） |
| `endpoint` | 否 | - | OBS endpoint 覆盖（缺省 `obs.<region>.myhuaweicloud.com`） |
| `header` | 否 | - | 额外请求头，如 `Authorization: Bearer xxx` |

**输出**：Workflow 日志输出预签名下载链接（默认 7 天有效），文件到期自动删除。

## 用法 - 镜像中转到 SWR

```bash
gh workflow run img-to-swr.yml --repo link-seek/url2hc \
  -f source_image="ghcr.io/anomalyco/opencode:latest"
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `source_image` | 是 | `ghcr.io/anomalyco/opencode:latest` | 源镜像地址 |
| `target_name` | 否 | 源镜像 repo 名 | SWR 上的镜像名 |
| `target_tag` | 否 | 源镜像 tag | SWR 上的标签 |
| `swr_region` | 否 | `cn-north-9` | SWR 区域（登录、公开+老化全跟着走） |
| `swr_registry` | 否 | - | registry 覆盖（缺省 `swr.<region>.myhuaweicloud.com`） |
| `swr_namespace` | 否 | `link-seek` | SWR 组织名 |
| `is_public` | 否 | `true` | 是否公开可拉取 |
| `expire_days` | 否 | `7` | 老化天数（`<=0` 跳过老化规则） |
| `tag_pattern` | 否 | `.*` | 老化 tag 正则 |

拉取地址：`<registry>/<namespace>/<镜像名>:<标签>`。

> 注意：SWR 按区域隔离存储。同区域 ECS 可内网拉取，跨区域需公网。k3s 在 `cn-north-9`，默认 `swr_region=cn-north-9`。

## 用法 - Dockerfile 构建并推送到 SWR

```bash
gh workflow run build-to-swr.yml --repo link-seek/url2hc \
  -f target_name="markitdown" \
  -f target_tag="0.1.7" \
  -f dockerfile_url="https://example.com/Dockerfile"
# 或直接内联 Dockerfile 内容：
gh workflow run build-to-swr.yml --repo link-seek/url2hc \
  -f target_name="markitdown" \
  -f target_tag="0.1.7" \
  -f dockerfile_inline="$(cat Dockerfile)"
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `dockerfile_inline` | 二选一 | - | Dockerfile 文本内容（与 url 二选一，优先用它） |
| `dockerfile_url` | 二选一 | - | Dockerfile 下载地址（inline 为空时使用） |
| `target_name` | 是 | - | SWR 上的镜像名 |
| `target_tag` | 否 | `latest` | SWR 上的标签 |
| `build_args` | 否 | - | 构建参数，多行 `KEY=VAL` |
| `swr_registry` | 否 | - | registry 覆盖（缺省 `swr.<region>.myhuaweicloud.com`） |
| `swr_namespace` | 否 | `link-seek` | SWR 组织名 |
| `swr_region` | 否 | `cn-north-4` | 公开+老化用的区域 |
| `is_public` | 否 | `true` | 是否公开可拉取 |
| `expire_days` | 否 | `7` | 老化天数（`<=0` 跳过） |
| `tag_pattern` | 否 | `.*` | 老化 tag 正则 |

> 注意：SWR 按区域隔离存储。同区域 ECS 可内网拉取，跨区域需公网。
