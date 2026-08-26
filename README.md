# url2hc

URL/镜像中转到华为云（OBS + SWR）。

## 用法 - 文件下载到 OBS

```bash
gh workflow run download-to-obs.yml --repo link-seek/url2hc \
  -f url="https://example.com/file.tar.gz" \
  -f obs_key="file.tar.gz"
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | 是 | - | 下载地址 |
| `obs_key` | 否 | `<文件名>` | `下载/` 下的相对路径 |
| `bucket` | 否 | `xieyucheng` | OBS 桶名 |
| `region` | 否 | `cn-north-9` | OBS 区域 |
| `header` | 否 | - | 额外请求头，如 `Authorization: Bearer xxx` |

**输出**：Workflow 日志输出 7 天有效的预签名下载链接，文件 7 天后自动删除。

## 用法 - 镜像中转到 SWR

```bash
gh workflow run img-to-swr.yml --repo link-seek/url2hc \
  -f source_image="anomalyco/opencode:latest"
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `source_image` | 是 | `anomalyco/opencode:latest` | 源镜像地址 |
| `target_name` | 否 | 源镜像 repo 名 | SWR 上的镜像名 |
| `target_tag` | 否 | 源镜像 tag | SWR 上的标签 |

**输出**：镜像自动设为公开可拉取，并设置 7 天存活时间老化规则。

拉取地址：`swr.cn-north-9.myhuaweicloud.com/link-seek/<镜像名>:<标签>`

## SWR 登录

```bash
docker login -u cn-north-9@HPUAJCDRH2SS4HYOAFK7 -p <token> swr.cn-north-9.myhuaweicloud.com
```
