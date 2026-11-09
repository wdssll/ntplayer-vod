# ntPlayer 影视订阅源生成器 (暴风资源 + 量子资源)

这是一个专为 iOS **ntPlayer**（及其他支持标准 M3U 的播放器）打造的影视点播订阅聚合项目。

## 特点
- **双主力源聚合**：聚合 **暴风资源 (17万+)** 与 **量子资源 (16万+)** 最新的热播电影、电视剧、综艺、动漫、短剧。
- **专为 ntPlayer 优化**：自动提取高清海报（`tvg-logo`），按剧集自动分组（`group-title="分类 · 剧集名"`），体验极佳。

---

## 订阅地址 (导入 ntPlayer)

在 iOS 设备上打开 **ntPlayer** -> 点击右上角 **+** 号 -> 选择 **网络订阅 (URL)**：

### 1. 推荐：精简热门版（秒级加载，前 100 部最新热播）
```text
https://fastly.jsdelivr.net/gh/wdssll/ntplayer-vod@main/vod_lite.m3u
```
*(GitHub 原始直链)*:
```text
https://raw.githubusercontent.com/wdssll/ntplayer-vod/main/vod_lite.m3u
```

### 2. 完整版（包含更多剧集与电影）
```text
https://fastly.jsdelivr.net/gh/wdssll/ntplayer-vod@main/vod.m3u
```
*(GitHub 原始直链)*:
```text
https://raw.githubusercontent.com/wdssll/ntplayer-vod/main/vod.m3u
```

---

## 本地手动运行

```bash
# 运行采集脚本
python collector.py
```
运行后会在当前目录生成：
- `vod.m3u`（完整订阅文件）
- `vod_lite.m3u`（精简热门订阅文件）
