"""config.yaml 加载与解析。"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from index_score.config.exceptions import ConfigError
from index_score.config.models import (
    AppConfig,
    FactorConfig,
    IndexInfo,
    LLMConfig,
    ReportConfig,
    ScoreRange,
    ScoringConfig,
    ScoringTemplate,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("config.yaml")


def load_config(path: Path | str | None = None) -> AppConfig:
    """加载 config.yaml 并返回 AppConfig 实例。

    Args:
        path: 配置文件路径，默认为项目根目录下的 config.yaml。

    Returns:
        解析后的 AppConfig 实例。

    Raises:
        ConfigError: 文件不存在、格式错误或缺少必要字段。
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    raw = _read_yaml(config_path)
    return _parse_config(raw, config_path)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"配置文件格式错误: {path}\n{exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"配置文件顶层必须是字典: {path}")

    return data


def _parse_config(raw: dict, path: Path) -> AppConfig:
    try:
        indexes = _parse_indexes(raw["indexes"])
        scoring = _parse_scoring(raw["scoring"])
        score_ranges = _parse_score_ranges(raw["score_ranges"])
        llm = _parse_llm(raw["llm"])
        report = _parse_report(raw["report"])
    except KeyError as exc:
        raise ConfigError(f"配置文件缺少必要字段: {exc} (文件: {path})") from exc
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"配置文件字段格式错误: {exc} (文件: {path})") from exc

    return AppConfig(
        indexes=indexes,
        scoring=scoring,
        score_ranges=score_ranges,
        llm=llm,
        report=report,
    )


def _parse_indexes(items: list[dict]) -> list[IndexInfo]:
    return [
        IndexInfo(
            code=str(item["code"]),
            name=str(item["name"]),
            market=str(item["market"]),
            template=str(item["template"]),
        )
        for item in items
    ]


def _parse_scoring(raw: dict) -> ScoringConfig:
    templates: dict[str, ScoringTemplate] = {}
    for name, template_raw in raw["templates"].items():
        factors = [
            FactorConfig(
                field=str(f["field"]),
                weight=float(f["weight"]),
            )
            for f in template_raw["factors"]
        ]
        templates[name] = ScoringTemplate(name=name, factors=factors)

    return ScoringConfig(
        templates=templates,
        pe_percentile_years=int(raw["pe_percentile_years"]),
        dividend_yield_percentile_years=int(raw["dividend_yield_percentile_years"]),
        price_position_years=int(raw["price_position_years"]),
    )


def _parse_score_ranges(items: list[dict]) -> list[ScoreRange]:
    return [
        ScoreRange(
            max_percentile=float(item["max_percentile"]),
            score=int(item["score"]),
        )
        for item in items
    ]


def _parse_llm(raw: dict) -> LLMConfig:
    return LLMConfig(
        provider=str(raw["provider"]),
        model=str(raw["model"]),
        api_key_env=str(raw["api_key_env"]),
        base_url=str(raw.get("base_url", "")),
        timeout=int(raw.get("timeout", 30)),
    )


def _parse_report(raw: dict) -> ReportConfig:
    return ReportConfig(
        show_detail=bool(raw.get("show_detail", True)),
        sort_by=str(raw.get("sort_by", "score")),
    )
