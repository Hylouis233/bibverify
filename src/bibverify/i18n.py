"""User-facing Chinese and English messages."""

from __future__ import annotations

from typing import Any

TEXTS = {
    "CN": {
        "warning_config_not_found": "警告: 配置文件 {config_file} 不存在，使用默认配置",
        "loaded_entries": "已加载 {count} 条文献记录",
        "checking_entry": "[{current}/{total}] 正在检查: {key}",
        "original_title": "原标题: {title}",
        "querying_platform": "[{platform}] 查询中...",
        "found_match": "[{platform}] ✓ 找到匹配",
        "not_found": "[{platform}] ✗ 未找到",
        "skip_no_doi": "[{platform}] ✗ 跳过（需要 DOI）",
        "platform_not_implemented": "[{platform}] ✗ 平台未实现",
        "platform_error": "✗ {platform} 严重错误: {error}",
        "matched_title": "✓ 匹配到: {title}",
        "need_update": "→ 需要更新 ({count} 个字段有差异)",
        "verified_no_update": "→ 验证通过，无需更新",
        "all_platforms_no_match": "✗ 所有平台均未找到匹配",
        "unknown_platform": "✗ 未知平台: {platform}",
        "timeout": "{platform} 查询超时",
        "http_error": "{platform} HTTP 错误: {code}",
        "network_error": "{platform} 网络错误: {error}",
        "json_parse_error": "{platform} JSON 解析错误",
        "unknown_error": "{platform} 未知错误: {error}",
        "xml_parse_error": "{platform} XML 解析错误",
        "access_denied_403": "{platform} 访问被拒绝 (403) - 可能达到速率限制",
        "rate_limit_429": "{platform} 速率限制 - 建议添加 API key",
        "auth_failed_401": "{platform} 认证失败 - 请检查 API key",
        "not_found_404": "{platform} 未找到 (404)",
        "tool_title": "Bibverify - BibTeX 文献检查工具",
        "enabled_platforms": "启用平台 ({count}): {platforms}",
        "start_verification": "开始验证文献...",
        "verification_complete": "检查完成!",
        "total_checked": "总计检查: {count} 条文献",
        "verified_passed": "✓ 验证通过: {count} 条",
        "need_update_count": "↻ 需要更新: {count} 条",
        "not_found_count": "✗ 未找到: {count} 条",
        "errors_count": "错误: {count} 条",
        "verified_sources": "验证通过的数据来源:",
        "update_sources": "更新数据的来源:",
        "generating_files": "正在生成文件...",
        "report_generated": "报告已生成: {file}",
        "backup_generated": "[1/3] 原始完整备份已生成: {file}",
        "updated_generated": "[2/3] 更新文献已生成: {file}",
        "updated_count": "包含: {count} 条找到并更新的文献",
        "no_update_skip": "[2/3] 无需更新的文献，跳过生成 updated 文件",
        "wrong_generated": "[3/3] 问题文献已生成: {file}",
        "wrong_count": "包含: {not_found} 条未找到 + {errors} 条错误",
        "no_wrong_skip": "[3/3] 无问题文献，跳过生成 wrong 文件",
        "missing_optional_dependency": "{platform} 可选依赖缺失: {dependency}，请安装后重试或禁用该平台",
        "doi_not_found": "未能通过 DOI 找到文献: {doi}",
        "skip_enrichment_only": "[{platform}] ✗ 跳过（仅用于开放获取补充，不作为文献元数据源）",
    },
    "EN": {
        "warning_config_not_found": "Warning: Configuration file {config_file} not found, using default config",
        "loaded_entries": "Loaded {count} bibliographic entries",
        "checking_entry": "[{current}/{total}] Checking: {key}",
        "original_title": "Original title: {title}",
        "querying_platform": "[{platform}] Querying...",
        "found_match": "[{platform}] ✓ Found match",
        "not_found": "[{platform}] ✗ Not found",
        "skip_no_doi": "[{platform}] ✗ Skip (DOI required)",
        "platform_not_implemented": "[{platform}] ✗ Platform not implemented",
        "platform_error": "✗ {platform} critical error: {error}",
        "matched_title": "✓ Matched: {title}",
        "need_update": "→ Need update ({count} fields differ)",
        "verified_no_update": "→ Verified, no update needed",
        "all_platforms_no_match": "✗ No match found on all platforms",
        "unknown_platform": "✗ Unknown platform: {platform}",
        "timeout": "{platform} query timeout",
        "http_error": "{platform} HTTP error: {code}",
        "network_error": "{platform} network error: {error}",
        "json_parse_error": "{platform} JSON parse error",
        "unknown_error": "{platform} unknown error: {error}",
        "xml_parse_error": "{platform} XML parse error",
        "access_denied_403": "{platform} access denied (403) - possibly rate limited",
        "rate_limit_429": "{platform} rate limit - recommend adding API key",
        "auth_failed_401": "{platform} authentication failed - please check API key",
        "not_found_404": "{platform} not found (404)",
        "tool_title": "Bibverify - BibTeX Literature Checker",
        "enabled_platforms": "Enabled platforms ({count}): {platforms}",
        "start_verification": "Starting literature verification...",
        "verification_complete": "Verification complete!",
        "total_checked": "Total checked: {count} entries",
        "verified_passed": "✓ Verified: {count} entries",
        "need_update_count": "↻ Need update: {count} entries",
        "not_found_count": "✗ Not found: {count} entries",
        "errors_count": "Errors: {count} entries",
        "verified_sources": "Verified data sources:",
        "update_sources": "Update data sources:",
        "generating_files": "Generating files...",
        "report_generated": "Report generated: {file}",
        "backup_generated": "[1/3] Original backup generated: {file}",
        "updated_generated": "[2/3] Updated entries generated: {file}",
        "updated_count": "Contains: {count} found and updated entries",
        "no_update_skip": "[2/3] No updates needed, skipping updated file generation",
        "wrong_generated": "[3/3] Problem entries generated: {file}",
        "wrong_count": "Contains: {not_found} not found + {errors} errors",
        "no_wrong_skip": "[3/3] No problem entries, skipping wrong file generation",
        "missing_optional_dependency": "{platform} optional dependency missing: {dependency}; install it or disable the platform",
        "doi_not_found": "Could not find a reference for DOI: {doi}",
        "skip_enrichment_only": "[{platform}] ✗ Skipped (open-access enrichment only, not bibliographic metadata)",
    },
}


class LanguageSupport:
    """Resolve localized messages and bilingual provider descriptions."""

    def __init__(self, language: str = "CN") -> None:
        self.language = language if language in TEXTS else "CN"

    def get_text(self, text_key: str, **kwargs: Any) -> str:
        text = TEXTS[self.language].get(text_key, text_key)
        return text.format(**kwargs) if kwargs else text

    def get_platform_description(self, platform_config: dict[str, Any]) -> str:
        description = str(platform_config.get("description", ""))
        if " / " not in description:
            return description
        chinese, english = description.split(" / ", 1)
        return english if self.language == "EN" else chinese
