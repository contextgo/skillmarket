#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
SOURCE_JSON = ROOT / "market" / "data" / "skills.json"
OUT_CURATED = ROOT / "market" / "data" / "curated_skills.json"
OUT_STATS = ROOT / "market" / "data" / "curated_stats.json"
OUT_INDUSTRIES = ROOT / "market" / "data" / "industry_index.json"
OUT_BUNDLES = ROOT / "market" / "data" / "bundles.json"
OUT_REPORT = ROOT / "market" / "data" / "curation_report.json"

GENERIC_TOKENS = {
    "skill",
    "skills",
    "agent",
    "agents",
    "tool",
    "tools",
    "assistant",
    "assistants",
    "auto",
    "ai",
    "the",
    "for",
    "with",
    "and",
    "of",
    "to",
    "a",
    "an",
    "pro",
    "plus",
    "hub",
    "platform",
    "system",
    "app",
    "service",
    "services",
    "openclaw",
    "claw",
    "contextgo",
}

THEMES: Dict[str, Dict[str, object]] = {
    "browser": {"label": "浏览器操作", "patterns": ["browser", "chrome", "edge", "brave", "web", "scraping", "scraper", "crawl", "crawler", "网页"]},
    "search": {"label": "搜索研究", "patterns": ["search", "搜索", "research", "检索"]},
    "xhs": {"label": "小红书", "patterns": ["xhs", "xiaohongshu", "redbook", "小红书"]},
    "wechat": {"label": "微信企微", "patterns": ["wechat", "wecom", "微信", "企微"]},
    "feishu": {"label": "飞书协同", "patterns": ["feishu", "飞书", "lark"]},
    "notion": {"label": "Notion", "patterns": ["notion"]},
    "github": {"label": "GitHub", "patterns": ["github", "gitlab", "git"]},
    "email": {"label": "邮件工作流", "patterns": ["email", "mail", "邮件"]},
    "seo": {"label": "SEO", "patterns": ["seo"]},
    "content": {"label": "内容写作", "patterns": ["content", "copywriting", "writer", "writing", "文案", "写作", "blog", "post", "article", "营销"]},
    "image": {"label": "图像生成", "patterns": ["image", "图片", "图像", "poster", "海报"]},
    "video": {"label": "视频生成", "patterns": ["video", "视频"]},
    "audio": {"label": "音频语音", "patterns": ["audio", "voice", "podcast", "tts", "asr", "音频", "语音"]},
    "ppt": {"label": "幻灯片", "patterns": ["ppt", "slide", "slides", "deck", "幻灯片"]},
    "pdf": {"label": "PDF", "patterns": ["pdf"]},
    "report": {"label": "报告生成", "patterns": ["report", "报告", "日报", "周报"]},
    "finance": {"label": "金融投研", "patterns": ["finance", "financial", "stock", "crypto", "trading", "fund", "财务", "金融", "股票"]},
    "crm": {"label": "销售获客", "patterns": ["crm", "lead", "sales", "销售", "获客"]},
    "customer_support": {"label": "客服支持", "patterns": ["support", "客服", "ticket"]},
    "calendar": {"label": "日程会议", "patterns": ["calendar", "schedule", "会议"]},
    "form": {"label": "表单采集", "patterns": ["form", "survey", "表单"]},
    "sheet": {"label": "表格处理", "patterns": ["excel", "spreadsheet", "sheet", "sheets", "表格"]},
    "database": {"label": "数据库", "patterns": ["database", "sql", "postgres", "mysql", "sqlite"]},
    "api": {"label": "API 集成", "patterns": ["api", "sdk"]},
    "cli": {"label": "CLI", "patterns": ["cli", "terminal", "command", "shell"]},
    "code": {"label": "代码开发", "patterns": ["code", "coding", "开发", "代码"]},
    "test": {"label": "测试 QA", "patterns": ["test", "testing", "qa"]},
    "deploy": {"label": "部署发布", "patterns": ["deploy", "deployment", "release", "vercel", "cloudflare"]},
    "monitor": {"label": "监控告警", "patterns": ["monitor", "alert", "监控", "告警", "tracker"]},
    "analytics": {"label": "分析洞察", "patterns": ["analytics", "analysis", "dashboard", "insight", "数据分析", "分析"]},
    "memory": {"label": "知识记忆", "patterns": ["memory", "memo", "知识库", "记忆"]},
    "prompt": {"label": "提示工程", "patterns": ["prompt"]},
    "translation": {"label": "翻译本地化", "patterns": ["translate", "translation", "翻译"]},
    "ocr": {"label": "OCR", "patterns": ["ocr"]},
    "doc": {"label": "文档处理", "patterns": ["doc", "docs", "documentation", "文档"]},
    "legal": {"label": "法务合规", "patterns": ["legal", "compliance", "合同", "法务", "合规"]},
    "security": {"label": "安全权限", "patterns": ["security", "auth", "permission", "安全"]},
    "automation": {"label": "流程自动化", "patterns": ["automation", "workflow", "sync", "integration", "自动化"]},
    "social": {"label": "社媒分发", "patterns": ["social", "twitter", "x.com", "linkedin", "facebook", "instagram"]},
    "youtube": {"label": "YouTube", "patterns": ["youtube"]},
    "ecommerce": {"label": "电商运营", "patterns": ["shopify", "amazon", "淘宝", "电商"]},
}

THEME_REGEX = {
    name: [re.compile(re.escape(pattern), re.IGNORECASE) for pattern in config["patterns"]]  # type: ignore[index]
    for name, config in THEMES.items()
}

INDUSTRIES: Dict[str, Dict[str, object]] = {
    "content-marketing": {
        "label": "内容营销",
        "summary": "选题、文案、社媒分发、小红书和 SEO 相关能力。",
        "themes": ["xhs", "content", "seo", "social", "youtube", "image", "video"],
        "problems": ["内容产能不稳定", "不同平台素材要重复改写", "缺少从研究到发布的闭环"],
        "useCases": ["选题策划与热点研究", "小红书和 SEO 内容生产", "图文视频素材生成与分发"],
        "outcomes": ["稳定输出内容流水线", "缩短从选题到发布的周期", "减少人工改稿和搬运"],
        "workflow": ["研究热点", "生成文案", "补齐视觉素材", "自动分发与复盘"],
    },
    "sales-ops": {
        "label": "销售获客",
        "summary": "线索采集、邮件触达、CRM 跟进和客户沟通。",
        "themes": ["crm", "email", "form", "sheet", "search", "wechat"],
        "problems": ["线索来源零散", "跟进动作不连续", "CRM 更新依赖人工维护"],
        "useCases": ["线索搜索与清洗", "邮件和企微触达", "CRM 同步与漏斗管理"],
        "outcomes": ["形成标准化获客漏斗", "减少线索流失", "让销售动作更可追踪"],
        "workflow": ["搜索目标客户", "收集并清洗线索", "多渠道触达", "沉淀到 CRM 并跟进"],
    },
    "customer-support": {
        "label": "客户支持",
        "summary": "客服回复、FAQ、工单处理和知识答疑。",
        "themes": ["customer_support", "doc", "search", "wechat", "feishu"],
        "problems": ["重复问答占用人工", "知识分散在文档和群聊", "工单处理不一致"],
        "useCases": ["FAQ 自动回复", "知识库检索问答", "客服消息与工单辅助处理"],
        "outcomes": ["缩短响应时间", "提升答案一致性", "让知识持续沉淀"],
        "workflow": ["汇总知识", "检索匹配答案", "生成回复建议", "同步记录与升级处理"],
    },
    "research-analysis": {
        "label": "研究分析",
        "summary": "搜索、抓取、监控、数据分析和报告生成。",
        "themes": ["browser", "search", "analytics", "report", "monitor", "finance"],
        "problems": ["研究信息散在多个来源", "监控和复盘依赖手工收集", "报告难以稳定输出"],
        "useCases": ["行业研究", "竞品监控", "日报周报和专题报告"],
        "outcomes": ["建立标准研究台", "让监控和分析形成例行化", "提高报告生成效率"],
        "workflow": ["抓取信息", "结构化整理", "监控告警", "生成分析报告"],
    },
    "engineering": {
        "label": "研发工程",
        "summary": "代码、CLI、API、测试、部署、文档和安全能力。",
        "themes": ["github", "api", "cli", "code", "test", "deploy", "memory", "prompt", "doc", "security"],
        "problems": ["代码协作链路长", "测试和文档容易被忽略", "发布和安全检查不稳定"],
        "useCases": ["代码开发与审查", "测试生成与质量检查", "文档维护和部署发布"],
        "outcomes": ["减少重复工程动作", "补齐质量门禁", "提升研发协作效率"],
        "workflow": ["读取仓库上下文", "生成或审查代码", "执行测试与安全检查", "部署交付并记录"],
    },
    "office-ops": {
        "label": "办公协同",
        "summary": "Notion、飞书、日程、表单、表格和流程自动化。",
        "themes": ["automation", "notion", "feishu", "calendar", "form", "sheet", "database"],
        "problems": ["表单、表格、文档互相割裂", "协同动作靠人工转发", "内部流程缺少统一编排"],
        "useCases": ["表单收集与表格处理", "飞书/Notion 协同", "日常审批和通知自动化"],
        "outcomes": ["减少重复录入", "让流程可追踪", "让协同工具真正串起来"],
        "workflow": ["采集信息", "同步知识与任务", "编排流程节点", "统一通知与归档"],
    },
    "design-media": {
        "label": "设计多媒体",
        "summary": "图片、视频、音频、PPT、PDF 和 OCR 相关能力。",
        "themes": ["image", "video", "audio", "ppt", "pdf", "ocr"],
        "problems": ["素材制作耗时", "多媒体产物风格不一致", "内容转换链路断裂"],
        "useCases": ["图片和海报生成", "视频脚本与视频产出", "PPT、PDF、OCR 转换处理"],
        "outcomes": ["加快多媒体制作", "把不同格式串成流程", "减少纯手工设计工作"],
        "workflow": ["准备素材", "生成视觉或音视频", "导出文档演示", "做格式转换与分发"],
    },
    "finance-investing": {
        "label": "金融投研",
        "summary": "市场监控、财报解读、股票和加密资产分析。",
        "themes": ["finance", "analytics", "report", "monitor", "search"],
        "problems": ["行情、新闻、财报分散", "监控靠人工盯盘", "投研结论沉淀困难"],
        "useCases": ["市场新闻监控", "财报和标的分析", "加密和股票研究支持"],
        "outcomes": ["形成持续投研工作台", "降低信息遗漏", "提高研究输出频率"],
        "workflow": ["拉取市场信息", "跟踪监控", "做结构化分析", "输出结论和报告"],
    },
    "legal-security": {
        "label": "法务安全",
        "summary": "权限校验、合规、风控、审计和法律文本处理。",
        "themes": ["legal", "security", "doc", "report"],
        "problems": ["权限和合规规则散落", "审计动作滞后", "法律文档处理效率低"],
        "useCases": ["权限和操作校验", "合规与风控审计", "合同与制度文本处理"],
        "outcomes": ["让风险前置", "减少人工审阅成本", "提高留痕与可审计性"],
        "workflow": ["识别风险点", "执行校验", "汇总审计结果", "生成整改或合规输出"],
    },
}

CATEGORY_THEME_MAP = {
    "developer-tools": ["code", "cli", "api"],
    "productivity": ["automation", "doc"],
    "data-analysis": ["analytics", "report"],
    "ai-intelligence": ["search", "prompt"],
    "content-creation": ["content", "image"],
    "security-compliance": ["security", "legal"],
    "communication-collaboration": ["feishu", "wechat", "email"],
    "javascript": ["code"],
    "python": ["code"],
    "html": ["code"],
    "development": ["code"],
    "marketing": ["content", "seo"],
    "finance": ["finance", "analytics"],
    "audio": ["audio"],
    "social-media": ["social"],
    "business": ["crm"],
    "design/visual": ["image", "ppt"],
    "设计/视觉": ["image", "ppt"],
    "写作/内容": ["content"],
    "tool": ["automation"],
    "utility": ["automation"],
}

BUNDLE_TEMPLATES: List[Dict[str, object]] = [
    {
        "id": "content-engine",
        "title": "内容增长组合",
        "summary": "从选题研究到文案、配图与发布，覆盖内容营销全链路。",
        "industries": ["content-marketing"],
        "forTeams": "内容团队、增长团队、品牌团队",
        "deliverables": ["选题池", "多平台文案", "配图或短视频素材", "发布动作清单"],
        "valuePoints": ["减少内容重复生产", "适合做持续内容流水线", "先研究再生成，避免纯堆内容"],
        "steps": [
            {"label": "热点研究", "themes": ["search", "analytics"]},
            {"label": "文案生成", "themes": ["content", "seo", "xhs"]},
            {"label": "视觉素材", "themes": ["image", "video", "ppt"]},
            {"label": "分发发布", "themes": ["social", "wechat", "automation"]},
        ],
    },
    {
        "id": "sales-pipeline",
        "title": "销售获客组合",
        "summary": "把线索收集、清洗、触达和 CRM 跟进串成一条流水线。",
        "industries": ["sales-ops"],
        "forTeams": "销售、BD、增长运营团队",
        "deliverables": ["目标线索清单", "触达文案", "CRM 跟进记录", "漏斗状态视图"],
        "valuePoints": ["把线索搜索和触达连起来", "减少 CRM 漏更", "适合中小团队快速起步"],
        "steps": [
            {"label": "线索搜索", "themes": ["search", "browser"]},
            {"label": "表单收集", "themes": ["form", "sheet"]},
            {"label": "触达沟通", "themes": ["email", "wechat", "crm"]},
            {"label": "流程同步", "themes": ["automation", "database", "notion"]},
        ],
    },
    {
        "id": "research-desk",
        "title": "研究分析组合",
        "summary": "适合做行业研究、市场监控、日报周报和投研支持。",
        "industries": ["research-analysis", "finance-investing"],
        "forTeams": "研究、战略、投研、运营分析团队",
        "deliverables": ["监控列表", "研究资料池", "日报周报", "专题分析结论"],
        "valuePoints": ["把搜索、抓取、监控、报告串起来", "适合做持续研究桌面", "对高频信息更新场景更有效"],
        "steps": [
            {"label": "信息抓取", "themes": ["browser", "search"]},
            {"label": "监控告警", "themes": ["monitor", "analytics"]},
            {"label": "报告生成", "themes": ["report", "pdf"]},
            {"label": "投研解读", "themes": ["finance", "analytics"]},
        ],
    },
    {
        "id": "engineering-copilot",
        "title": "研发协作组合",
        "summary": "面向开发团队的代码、测试、文档和发布协同。",
        "industries": ["engineering"],
        "forTeams": "研发、平台、DevOps 团队",
        "deliverables": ["代码改动建议", "测试检查项", "工程文档", "发布前检查清单"],
        "valuePoints": ["减少上下文切换", "补齐测试和文档短板", "把开发与交付串成连续动作"],
        "steps": [
            {"label": "代码与仓库", "themes": ["code", "github", "cli"]},
            {"label": "测试质量", "themes": ["test", "security"]},
            {"label": "知识文档", "themes": ["doc", "memory", "prompt"]},
            {"label": "部署交付", "themes": ["deploy", "api"]},
        ],
    },
    {
        "id": "office-automation",
        "title": "办公自动化组合",
        "summary": "适合把飞书、Notion、表单和日程串成低门槛自动化流程。",
        "industries": ["office-ops"],
        "forTeams": "运营、行政、项目管理、综合支持团队",
        "deliverables": ["收集表单", "协同知识页", "流程任务流", "自动通知记录"],
        "valuePoints": ["把零散协同工具真正串起来", "低门槛落地自动化", "适合大量日常重复动作"],
        "steps": [
            {"label": "信息采集", "themes": ["form", "sheet", "calendar"]},
            {"label": "知识沉淀", "themes": ["notion", "feishu", "doc"]},
            {"label": "流程编排", "themes": ["automation", "database"]},
            {"label": "同步通知", "themes": ["email", "wechat", "feishu"]},
        ],
    },
]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def item_text(item: Dict[str, object]) -> str:
    return " ".join(
        [
            str(item.get("displayName", "") or ""),
            str(item.get("name", "") or ""),
            str(item.get("description", "") or ""),
            " ".join(item.get("tags", []) or []),
            " ".join(item.get("categories", []) or []),
        ]
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fallback_token(item: Dict[str, object]) -> str:
    for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", item_text(item).lower()):
        if len(token) <= 2 or token in GENERIC_TOKENS or token.isdigit():
            continue
        return token
    return normalize_text(str(item.get("displayName") or item.get("name") or "misc")).replace(" ", "-")[:20] or "misc"


def match_themes(item: Dict[str, object]) -> List[str]:
    text = item_text(item)
    matched = set()
    for name, patterns in THEME_REGEX.items():
        if any(pattern.search(text) for pattern in patterns):
            matched.add(name)
    for category in item.get("categories", []) or []:
        normalized = normalize_text(str(category))
        for theme in CATEGORY_THEME_MAP.get(normalized, []):
            matched.add(theme)
    return sorted(matched)


def primary_capability(themes: Sequence[str]) -> str:
    theme_set = set(themes)
    if theme_set & {"xhs", "wechat", "feishu", "seo", "content", "social", "youtube"}:
        return "增长运营"
    if theme_set & {"browser", "search"}:
        return "信息研究"
    if theme_set & {"finance", "analytics", "report", "monitor"}:
        return "分析洞察"
    if theme_set & {"image", "video", "audio", "ppt", "pdf", "ocr"}:
        return "多媒体制作"
    if theme_set & {"automation", "crm", "email", "calendar", "form", "sheet", "database", "notion"}:
        return "流程协同"
    if theme_set & {"github", "api", "cli", "code", "test", "deploy", "memory", "prompt", "doc", "security", "legal"}:
        return "研发工程"
    return "通用能力"


def detect_industries(themes: Sequence[str]) -> List[str]:
    theme_set = set(themes)
    matched = []
    for industry_id, config in INDUSTRIES.items():
        related = set(config["themes"])  # type: ignore[arg-type]
        if theme_set & related:
            matched.append(industry_id)
    return matched or ["office-ops"]


def log_score(value: int, weight: float) -> float:
    return math.log1p(max(0, int(value))) * weight


def compute_quality_score(item: Dict[str, object]) -> int:
    metrics = item.get("metrics", {}) or {}
    name = normalize_text(str(item.get("displayName") or item.get("name") or ""))
    tags = item.get("tags", []) or []
    categories = item.get("categories", []) or []
    sources = item.get("sources", []) or []

    score = 0.0
    score += log_score(metrics.get("skillhub_downloads", 0), 10)  # type: ignore[arg-type]
    score += log_score(metrics.get("skillhub_installs", 0) + metrics.get("openclawmp_installs", 0), 16)  # type: ignore[arg-type]
    score += log_score(
        metrics.get("skillhub_stars", 0) + metrics.get("openclawmp_total_stars", 0) + metrics.get("openclawmp_github_stars", 0), 18  # type: ignore[arg-type]
    )
    score += len(sources) * 10
    score += 4 if item.get("description") else -8
    score += 3 if item.get("archives") else -6
    score += 3 if item.get("readmeUrl") else 0
    score += min(len(tags), 5)
    score += 4 if categories else 0

    if name in {"skill", "test", "demo", "example", "openclaw skill"}:
        score -= 25
    if len(name) <= 3:
        score -= 10

    return int(round(score))


def cluster_key(item: Dict[str, object], themes: Sequence[str]) -> str:
    capability = primary_capability(themes)
    if themes:
        return capability + "::" + "+".join(sorted(themes)[:2])
    categories = item.get("categories", []) or []
    category = normalize_text(str(categories[0])) if categories else "misc"
    return capability + "::" + category + "::" + fallback_token(item)


def selection_reason(item: Dict[str, object], cluster_size: int) -> str:
    reasons = []
    sources = item.get("sources", []) or []
    if len(sources) == 2:
        reasons.append("双源重合")
    if cluster_size >= 12:
        reasons.append("同类功能中保留头部")
    if item.get("readmeUrl"):
        reasons.append("信息完整")
    metrics = item.get("metrics", {}) or {}
    installs = int(metrics.get("skillhub_installs", 0) or 0) + int(metrics.get("openclawmp_installs", 0) or 0)
    downloads = int(metrics.get("skillhub_downloads", 0) or 0)
    stars = int(metrics.get("skillhub_stars", 0) or 0) + int(metrics.get("openclawmp_total_stars", 0) or 0)
    if max(installs, downloads, stars) > 500:
        reasons.append("热度较高")
    if not reasons:
        reasons.append("覆盖稀缺能力")
    return "，".join(reasons[:3])


def enrich_items(items: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    enriched = []
    for item in items:
        themes = match_themes(item)
        industries = detect_industries(themes)
        cluster = cluster_key(item, themes)
        enriched.append(
            {
                **item,
                "themes": themes,
                "industries": industries,
                "primaryCapability": primary_capability(themes),
                "qualityScore": compute_quality_score(item),
                "clusterKey": cluster,
            }
        )
    return enriched


def curate_items(items: List[Dict[str, object]]) -> tuple[List[Dict[str, object]], Dict[str, int]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for item in items:
        grouped[str(item["clusterKey"])].append(item)

    selected: List[Dict[str, object]] = []
    cluster_sizes = {key: len(rows) for key, rows in grouped.items()}

    for key, rows in grouped.items():
        rows.sort(
            key=lambda row: (
                -int(row.get("qualityScore", 0)),
                -int(row.get("popularity", 0)),
                normalize_text(str(row.get("displayName") or row.get("name") or "")),
            )
        )
        limit = 1
        if len(rows) >= 12:
            limit = 2
        if len(rows) >= 50:
            limit = 3
        for row in rows[:limit]:
            if not row.get("themes") and int(row.get("qualityScore", 0)) < 60:
                continue
            row["clusterSize"] = len(rows)
            row["selectionReason"] = selection_reason(row, len(rows))
            selected.append(row)

    selected.sort(
        key=lambda row: (
            -int(row.get("qualityScore", 0)),
            -int(row.get("popularity", 0)),
            normalize_text(str(row.get("displayName") or row.get("name") or "")),
        )
    )
    return selected, cluster_sizes


def aggregate_source_counts(items: Sequence[Dict[str, object]]) -> Dict[str, int]:
    counts = {"skillhub": 0, "openclawmp": 0, "merged": 0}
    for item in items:
        sources = set(item.get("sources", []) or [])
        if sources == {"skillhub", "openclawmp"}:
            counts["merged"] += 1
        elif sources == {"skillhub"}:
            counts["skillhub"] += 1
        elif sources == {"openclawmp"}:
            counts["openclawmp"] += 1
    return counts


def build_industry_index(items: Sequence[Dict[str, object]]) -> Dict[str, object]:
    industries_payload = []
    for industry_id, config in INDUSTRIES.items():
        rows = [item for item in items if industry_id in (item.get("industries") or [])]
        related_themes = set(config["themes"])  # type: ignore[arg-type]
        rows.sort(
            key=lambda row: (
                -len(related_themes & set(row.get("themes", []) or [])),
                len(row.get("themes", []) or []),
                -int(row.get("qualityScore", 0)),
                -int(row.get("popularity", 0)),
            )
        )
        theme_counter = Counter(theme for item in rows for theme in item.get("themes", []) or [])
        industries_payload.append(
            {
                "id": industry_id,
                "label": config["label"],
                "summary": config["summary"],
                "problems": config["problems"],
                "useCases": config["useCases"],
                "outcomes": config["outcomes"],
                "workflow": config["workflow"],
                "count": len(rows),
                "topSkillIds": [item["id"] for item in rows[:6]],
                "recommendedSkillIds": [item["id"] for item in rows[:3]],
                "topThemes": [THEMES[name]["label"] for name, _ in theme_counter.most_common(4)],
                "bundleIds": [bundle["id"] for bundle in BUNDLE_TEMPLATES if industry_id in bundle["industries"]],  # type: ignore[index]
            }
        )
    industries_payload.sort(key=lambda row: (-int(row["count"]), str(row["label"])))
    return {
        "generatedAt": utc_now_iso(),
        "industries": industries_payload,
    }


def pick_bundle_skill_ids(items: Sequence[Dict[str, object]], themes: Sequence[str], limit: int = 3) -> List[str]:
    theme_set = set(themes)
    rows = [item for item in items if theme_set & set(item.get("themes", []) or [])]
    rows.sort(
        key=lambda row: (
            -len(theme_set & set(row.get("themes", []) or [])),
            len(row.get("themes", []) or []),
            -int(row.get("qualityScore", 0)),
            -int(row.get("popularity", 0)),
        )
    )
    return [item["id"] for item in rows[:limit]]


def build_bundles(items: Sequence[Dict[str, object]]) -> Dict[str, object]:
    bundles = []
    for template in BUNDLE_TEMPLATES:
        steps = []
        skill_ids = []
        for step in template["steps"]:  # type: ignore[index]
            matched_ids = pick_bundle_skill_ids(items, step["themes"])  # type: ignore[index]
            skill_ids.extend(matched_ids)
            steps.append(
                {
                    "label": step["label"],
                    "themes": [THEMES[name]["label"] for name in step["themes"]],  # type: ignore[index]
                    "skillIds": matched_ids,
                }
            )
        deduped_ids = list(dict.fromkeys(skill_ids))
        bundles.append(
            {
                "id": template["id"],
                "title": template["title"],
                "summary": template["summary"],
                "industries": template["industries"],
                "forTeams": template["forTeams"],
                "deliverables": template["deliverables"],
                "valuePoints": template["valuePoints"],
                "steps": steps,
                "skillIds": deduped_ids[:10],
            }
        )
    return {
        "generatedAt": utc_now_iso(),
        "bundles": bundles,
    }


def build_stats(source_items: Sequence[Dict[str, object]], curated_items: Sequence[Dict[str, object]], cluster_sizes: Dict[str, int]) -> Dict[str, object]:
    industry_counter = Counter(industry for item in curated_items for industry in item.get("industries", []) or [])
    capability_counter = Counter(item.get("primaryCapability", "通用能力") for item in curated_items)
    reduction_ratio = 0.0
    if source_items:
        reduction_ratio = 1 - (len(curated_items) / len(source_items))

    return {
        "total": len(curated_items),
        "sourceTotal": len(source_items),
        "reducedCount": len(source_items) - len(curated_items),
        "reductionRatio": round(reduction_ratio, 4),
        "sources": aggregate_source_counts(curated_items),
        "topIndustries": [{"id": key, "label": INDUSTRIES[key]["label"], "count": value} for key, value in industry_counter.most_common(6)],
        "topCapabilities": [{"label": key, "count": value} for key, value in capability_counter.most_common(6)],
        "clusterCount": len(cluster_sizes),
        "generatedAt": utc_now_iso(),
    }


def build_report(source_items: Sequence[Dict[str, object]], curated_items: Sequence[Dict[str, object]], cluster_sizes: Dict[str, int]) -> Dict[str, object]:
    biggest_clusters = sorted(cluster_sizes.items(), key=lambda item: (-item[1], item[0]))[:20]
    return {
        "sourceTotal": len(source_items),
        "curatedTotal": len(curated_items),
        "clusterCount": len(cluster_sizes),
        "biggestClusters": [{"clusterKey": key, "size": size} for key, size in biggest_clusters],
        "topCuratedSkills": [
            {
                "id": item["id"],
                "displayName": item.get("displayName") or item.get("name"),
                "qualityScore": item.get("qualityScore", 0),
                "primaryCapability": item.get("primaryCapability", ""),
                "industries": item.get("industries", []),
            }
            for item in curated_items[:20]
        ],
        "generatedAt": utc_now_iso(),
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build_curated_outputs(source_items: Sequence[Dict[str, object]]) -> Dict[str, object]:
    enriched = enrich_items(source_items)
    curated_items, cluster_sizes = curate_items(enriched)

    curated_payload = {
        "generatedAt": utc_now_iso(),
        "items": curated_items,
    }
    stats_payload = build_stats(source_items, curated_items, cluster_sizes)
    industries_payload = build_industry_index(curated_items)
    bundles_payload = build_bundles(curated_items)
    report_payload = build_report(source_items, curated_items, cluster_sizes)

    write_json(OUT_CURATED, curated_payload)
    write_json(OUT_STATS, stats_payload)
    write_json(OUT_INDUSTRIES, industries_payload)
    write_json(OUT_BUNDLES, bundles_payload)
    write_json(OUT_REPORT, report_payload)

    return {
        "curatedTotal": len(curated_items),
        "sourceTotal": len(source_items),
        "clusterCount": len(cluster_sizes),
        "topIndustryCount": len(industries_payload["industries"]),
        "bundleCount": len(bundles_payload["bundles"]),
    }


def main() -> int:
    payload = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise SystemExit("market/data/skills.json 缺少 items 数组")
    summary = build_curated_outputs(items)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
