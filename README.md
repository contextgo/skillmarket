<p align="center">
  <img src="./market/assets/contextgo-readme-header.png" alt="ContextGo SkillMarket" width="100%">
</p>

<p align="center">
  <img src="./market/assets/contextgo-logo.png" alt="ContextGo Logo" width="108">
</p>

<p align="center">
  <strong>ContextGo SkillMarket</strong><br>
  面向 Agent 的技能发现、镜像、精选、组合与分发基础设施。
</p>

<p align="center">
  <a href="./README_EN.md">English</a> ·
  <a href="https://github.com/contextgo/contextgo">ContextGo 主仓</a> ·
  <a href="https://github.com/contextgo/skillmarket">GitHub</a>
</p>

---

## 这是什么

`skillmarket` 是 ContextGo 产品矩阵中的子项目，用来组织 Agent 技能生态。

它不是一个单纯的镜像脚本仓库，也不只是一个静态页面导出目录。它承担的是更完整的技能基础设施角色：

- 从上游生态抓取和镜像技能资产
- 生成可检索、可精选、可组合的 catalog
- 为 Agent 产品提供技能分发入口
- 为 ContextGo 以及其他 Agent 系统提供开放的技能供应层

---

## 它解决什么问题

随着 Agent 真正进入项目工作，技能资产会迅速出现几个典型问题：

- 技能分散在不同社区、仓库和临时链接里
- 技能质量差异很大，难以稳定复用
- 缺少精选、行业索引和组合包层
- 缺少一个既能服务产品，又能独立开源运转的技能市场基础设施

`skillmarket` 的目标，就是把“技能从哪里来、怎么被筛选、怎么被发布”这条链路打通。

---

## 在 ContextGo 里的角色

在 ContextGo 里，技能不是孤立提示词，而是 Agent Package 与工作流能力的一部分。

`skillmarket` 负责的不是 Agent 执行本身，而是技能供给层：

- 上游镜像
- 结构化 catalog
- 精选技能集
- 行业索引
- 组合包
- 可静态托管的市场站点输出

这样一来，ContextGo 的 Agent 助手、技能包和后续生态分发才有稳定的来源。

---

## 当前仓库提供什么

当前仓库已经包含两类上游镜像能力：

- `SkillHub`
- `openclawmp`

并围绕这些数据构建了一套市场输出流程：

- 全量 manifest
- 精选 manifest
- 行业索引
- bundles 组合数据
- 静态站点入口
- 部署流水线

这使它既可以作为内部供应层，也可以作为公开的开源技能市场基础设施。

---

## 快速开始

### 镜像 SkillHub

```bash
python3 scripts/skillhub_mirror.py --output-root mirror --page-size 100 --page-concurrency 8 --download-concurrency 12
python3 scripts/skillhub_recover_failed.py --output-root mirror
```

输出：

- `mirror/catalog/skills_catalog.json`
- `mirror/zips/`
- `mirror/reports/skills_table.csv`
- `mirror/reports/skills_summary.md`

### 镜像 openclawmp

```bash
python3 scripts/openclawmp_mirror.py --output-root openclawmp_mirror --type skill --page-limit 100 --download-concurrency 12
```

输出：

- `openclawmp_mirror/catalog/skills_catalog.json`
- `openclawmp_mirror/zips/`
- `openclawmp_mirror/reports/skills_table.csv`
- `openclawmp_mirror/reports/skills_summary.md`

### 生成市场数据

已实现一个可静态托管的技能市场页面：

- 页面入口：`market/index.html`
- 全量 manifest：`market/data/skills.json`
- 精选 manifest：`market/data/curated_skills.json`
- 组合数据：`market/data/industry_index.json`、`market/data/bundles.json`
- 生成脚本：`scripts/build_market_catalog.py`

---

## 部署与同步

仓库已包含自动化部署与同步流水线：

- 工作流：`.github/workflows/deploy.yml`
- 定时同步：`.github/workflows/sync-upstreams.yml`
- 部署脚本：`scripts/deploy_to_oss.py`
- 部署说明：`DEPLOYMENT.md`

当前同步流程会顺序执行：

- `scripts/skillhub_mirror.py`
- `scripts/skillhub_recover_failed.py`
- `scripts/openclawmp_mirror.py`
- `scripts/build_market_catalog.py`

如果 catalog 或站点数据发生变化，工作流会自动提交并继续部署。

---

## 为什么它独立开源

技能生态天然不应该被锁死在单一产品里。

`skillmarket` 被单独开源，是因为它本质上是一个 Agent 能力分发基础设施：

- 可以服务 ContextGo
- 也可以服务其他 Agent 平台或私有技能体系
- 既能做公开镜像，也能做精选和运营层

这层一旦稳定，Agent 的构建和复用成本就会明显下降。

---

## 和 ContextGo 的关系

如果你想了解完整产品，请看：

- [ContextGo 主仓](https://github.com/contextgo/contextgo)
- [Connector](https://github.com/contextgo/connector)
- [ContextGo Releases](https://github.com/contextgo/contextgo-releases)

`skillmarket` 负责技能供给与分发基础设施；Agent 工作台、Context Engine、多端远程访问和最终用户体验在主产品仓里。
