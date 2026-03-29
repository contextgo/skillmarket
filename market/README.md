# ContextGo Curated Skills

一个纯静态、可直接部署到 OSS / COS / CDN，并计划挂载到 `www.skillmarket.com.cn` 的技能市场页面。

品牌：`ContextGo`

域名：`www.skillmarket.com.cn`

## 页面入口

- `market/index.html`
- 样式：`market/assets/styles.css`
- 交互：`market/assets/app.js`
- 配置：`market/config.js`

## 数据文件

- `market/data/skills.json`：全量统一 manifest
- `market/data/stats.json`：全量统计
- `market/data/curated_skills.json`：首页默认使用的精选 manifest
- `market/data/curated_stats.json`：精选统计
- `market/data/industry_index.json`：行业入口索引
- `market/data/bundles.json`：组合包数据
- `market/data/curation_report.json`：精选过程摘要

## 重新生成 manifest

```bash
python3 scripts/build_market_catalog.py
```

当前会把两套数据按严格规则合并：

- `name + version + author`
- 输出总数：`27982`
- 当前精选集：`1211`

## 本地预览

```bash
python3 -m http.server 4317
# 打开 http://127.0.0.1:4317/market/
```

## OSS 托管建议

### 1. 上传页面资源

上传整个 `market/` 目录。

### 2. 上传压缩包

建议在 OSS 上按两套前缀放：

```text
packages/
  skillhub/
    <slug>/<version>.zip
  openclawmp/
    <asset-id>/<file>.zip
```

### 3. 修改配置

编辑 `market/config.js`：

```js
window.SKILL_MARKET_CONFIG = {
  brandName: 'ContextGo',
  siteUrl: 'https://www.skillmarket.com.cn',
  manifestUrl: 'https://your-cdn.example.com/market/data/curated_skills.json',
  statsUrl: 'https://your-cdn.example.com/market/data/curated_stats.json',
  fullManifestUrl: 'https://your-cdn.example.com/market/data/skills.json',
  fullStatsUrl: 'https://your-cdn.example.com/market/data/stats.json',
  industryUrl: 'https://your-cdn.example.com/market/data/industry_index.json',
  bundleUrl: 'https://your-cdn.example.com/market/data/bundles.json',
  packageBaseUrls: {
    skillhub: 'https://your-cdn.example.com/packages/skillhub/',
    openclawmp: 'https://your-cdn.example.com/packages/openclawmp/',
  },
  defaultView: 'curated',
};
```

## 当前默认本地配置

默认指向：

- `../mirror/zips/`
- `../openclawmp_mirror/zips/`

所以仓库内可直接预览。
