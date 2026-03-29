# Market Mirrors

本项目现在包含两套镜像工具：

- `scripts/skillhub_fetch.py`：最小化远程 `list/search/download`
- `scripts/skillhub_mirror.py`：全量镜像 `SkillHub`
- `scripts/skillhub_recover_failed.py`：补救 `SkillHub` 缺失 zip
- `scripts/openclawmp_mirror.py`：全量镜像 `openclawmp` 的 skills
- `scripts/build_curated_catalog.py`：从全量数据生成精选集、行业索引和组合包

## SkillHub

```bash
python3 scripts/skillhub_mirror.py --output-root mirror --page-size 100 --page-concurrency 8 --download-concurrency 12
python3 scripts/skillhub_recover_failed.py --output-root mirror
```

结果：

- `mirror/catalog/skills_catalog.json`
- `mirror/zips/`
- `mirror/reports/skills_table.csv`
- `mirror/reports/skills_summary.md`

## openclawmp

```bash
python3 scripts/openclawmp_mirror.py --output-root openclawmp_mirror --type skill --page-limit 100 --download-concurrency 12
```

结果：

- `openclawmp_mirror/catalog/skills_catalog.json`
- `openclawmp_mirror/zips/`
- `openclawmp_mirror/reports/skills_table.csv`
- `openclawmp_mirror/reports/skills_summary.md`

## Curated Skills Site

品牌：`ContextGo`

域名：`www.skillmarket.com.cn`

已实现一个可静态托管的技能市场页面：

- 页面入口：`market/index.html`
- 全量 manifest：`market/data/skills.json`
- 精选 manifest：`market/data/curated_skills.json`
- 生成脚本：`scripts/build_market_catalog.py`
- 组合数据：`market/data/industry_index.json`、`market/data/bundles.json`
- 说明文档：`market/README.md`

## CI/CD Deployment

已添加 GitHub Actions 自动部署流水线：

- 工作流：`.github/workflows/deploy.yml`
- 部署脚本：`scripts/deploy_to_oss.py`
- 说明文档：`DEPLOYMENT.md`

当 GitHub `main` 分支有新提交时，工作流会自动同步站点文件和技能包到 OSS。
