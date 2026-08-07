# url-to-obs

URL 文件下载中转到华为云 OBS。

## 用法

```bash
gh workflow run download-to-obs.yml --repo link-seek/url-to-obs \
  -f url="https://example.com/file.tar.gz" \
  -f obs_key="下载/file.tar.gz"
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | 是 | - | 下载地址 |
| `obs_key` | 否 | `下载/<文件名>` | OBS 目标路径 |
| `bucket` | 否 | `xieyucheng` | OBS 桶名 |
| `region` | 否 | `cn-north-9` | OBS 区域 |
| `header` | 否 | - | 额外请求头，如 `Authorization: Bearer xxx` |

## 输出

Workflow 运行日志中输出：
- **7 天有效的预签名下载链接**
- 文件 7 天后自动删除（OBS 生命周期规则）
