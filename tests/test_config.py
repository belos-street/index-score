"""配置加载模块测试。"""

from pathlib import Path

import pytest

from index_score.config.exceptions import ConfigError
from index_score.config.loader import load_config
from index_score.config.models import AppConfig


def _write_yaml(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def _min_config_yaml() -> str:
    return """\
indexes:
  - code: "000922"
    name: "中证红利"
    market: "CN"
    template: "dividend"

scoring:
  templates:
    dividend:
      factors:
        - { field: "dividend_yield_percentile_5y", weight: 0.40 }
        - { field: "pe_percentile_5y", weight: 0.35 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3

score_ranges:
  - max_percentile: 20
    score: 1
  - max_percentile: 100
    score: 9

llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key_env: "TEST_API_KEY"
  base_url: "https://api.deepseek.com"
  timeout: 30

report:
  show_detail: true
  sort_by: "score"
"""


class TestLoadConfig:
    def test_load_minimal_config(self, tmp_path: Path) -> None:
        config_path = _write_yaml(tmp_path, "config.yaml", _min_config_yaml())
        cfg = load_config(config_path)

        assert isinstance(cfg, AppConfig)
        assert len(cfg.indexes) == 1
        assert cfg.indexes[0].code == "000922"
        assert cfg.indexes[0].template == "dividend"

    def test_load_full_config(self, tmp_path: Path) -> None:
        full_yaml = """\
indexes:
  - code: "000922"
    name: "中证红利"
    market: "CN"
    template: "dividend"
  - code: "IXIC"
    name: "纳指"
    market: "US"
    template: "growth"

scoring:
  templates:
    dividend:
      factors:
        - { field: "dividend_yield_percentile_5y", weight: 0.40 }
        - { field: "pe_percentile_5y", weight: 0.35 }
        - { field: "price_position_percentile_3y", weight: 0.25 }
    growth:
      factors:
        - { field: "pe_percentile_5y", weight: 0.50 }
        - { field: "price_position_percentile_3y", weight: 0.35 }
        - { field: "dividend_yield_percentile_5y", weight: 0.15 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3

score_ranges:
  - max_percentile: 20
    score: 1
  - max_percentile: 40
    score: 3
  - max_percentile: 60
    score: 5
  - max_percentile: 80
    score: 7
  - max_percentile: 100
    score: 9

llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key_env: "TEST_API_KEY"
  base_url: "https://api.deepseek.com"
  timeout: 30

report:
  show_detail: true
  sort_by: "score"
"""
        config_path = _write_yaml(tmp_path, "config.yaml", full_yaml)
        cfg = load_config(config_path)

        assert len(cfg.indexes) == 2
        assert len(cfg.scoring.templates) == 2
        assert "dividend" in cfg.scoring.templates
        assert "growth" in cfg.scoring.templates
        assert len(cfg.score_ranges) == 5

    def test_load_real_project_config(self) -> None:
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            pytest.skip("project config.yaml not found")

        cfg = load_config(config_path)

        assert len(cfg.indexes) == 7
        assert len(cfg.scoring.templates) == 4
        assert cfg.scoring.pe_percentile_years == 5
        assert cfg.scoring.price_position_years == 3


class TestScoringTemplateParsing:
    def test_template_factors_parsed_correctly(self, tmp_path: Path) -> None:
        config_path = _write_yaml(tmp_path, "config.yaml", _min_config_yaml())
        cfg = load_config(config_path)

        dividend = cfg.scoring.templates["dividend"]
        assert dividend.name == "dividend"
        assert len(dividend.factors) == 2
        assert dividend.factors[0].field == "dividend_yield_percentile_5y"
        assert dividend.factors[0].weight == 0.40
        assert dividend.factors[1].field == "pe_percentile_5y"
        assert dividend.factors[1].weight == 0.35

    def test_all_four_templates(self, tmp_path: Path) -> None:
        full_yaml = """\
indexes:
  - code: "000922"
    name: "test"
    market: "CN"
    template: "dividend"
  - code: "399378"
    name: "test2"
    market: "CN"
    template: "value"
  - code: "IXIC"
    name: "test3"
    market: "US"
    template: "growth"
  - code: "SPX"
    name: "test4"
    market: "US"
    template: "balanced"

scoring:
  templates:
    dividend:
      factors:
        - { field: "dividend_yield_percentile_5y", weight: 0.40 }
        - { field: "pe_percentile_5y", weight: 0.35 }
        - { field: "price_position_percentile_3y", weight: 0.25 }
    value:
      factors:
        - { field: "pe_percentile_5y", weight: 0.40 }
        - { field: "pb_percentile_5y", weight: 0.30 }
        - { field: "dividend_yield_percentile_5y", weight: 0.30 }
    growth:
      factors:
        - { field: "pe_percentile_5y", weight: 0.50 }
        - { field: "price_position_percentile_3y", weight: 0.35 }
        - { field: "dividend_yield_percentile_5y", weight: 0.15 }
    balanced:
      factors:
        - { field: "pe_percentile_5y", weight: 0.35 }
        - { field: "dividend_yield_percentile_5y", weight: 0.35 }
        - { field: "price_position_percentile_3y", weight: 0.30 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3

score_ranges:
  - max_percentile: 20
    score: 1
  - max_percentile: 100
    score: 9

llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key_env: "TEST_API_KEY"
  base_url: "https://api.deepseek.com"
  timeout: 30

report:
  show_detail: true
  sort_by: "score"
"""
        config_path = _write_yaml(tmp_path, "config.yaml", full_yaml)
        cfg = load_config(config_path)

        assert len(cfg.scoring.templates) == 4

        dividend = cfg.scoring.templates["dividend"]
        assert len(dividend.factors) == 3
        assert sum(f.weight for f in dividend.factors) == pytest.approx(1.0)

        value = cfg.scoring.templates["value"]
        assert len(value.factors) == 3
        assert value.factors[1].field == "pb_percentile_5y"

        growth = cfg.scoring.templates["growth"]
        assert growth.factors[0].weight == 0.50

        balanced = cfg.scoring.templates["balanced"]
        assert balanced.factors[0].weight == 0.35


class TestLLMConfig:
    def test_api_key_from_env(self, tmp_path: Path) -> None:
        config_path = _write_yaml(tmp_path, "config.yaml", _min_config_yaml())
        cfg = load_config(config_path)

        assert cfg.llm.api_key_env == "TEST_API_KEY"
        assert cfg.llm.api_key == ""

    def test_api_key_from_env_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _write_yaml(tmp_path, "config.yaml", _min_config_yaml())
        cfg = load_config(config_path)

        monkeypatch.setenv("TEST_API_KEY", "sk-test123")
        assert cfg.llm.api_key == "sk-test123"

    def test_llm_defaults(self, tmp_path: Path) -> None:
        config_path = _write_yaml(tmp_path, "config.yaml", _min_config_yaml())
        cfg = load_config(config_path)

        assert cfg.llm.provider == "deepseek"
        assert cfg.llm.model == "deepseek-chat"
        assert cfg.llm.base_url == "https://api.deepseek.com"
        assert cfg.llm.timeout == 30


class TestConfigErrors:
    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="配置文件不存在"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{{{invalid", encoding="utf-8")
        with pytest.raises(ConfigError, match="配置文件格式错误"):
            load_config(bad)

    def test_not_a_dict(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "list.yaml", "- a\n- b\n")
        with pytest.raises(ConfigError, match="顶层必须是字典"):
            load_config(p)

    def test_missing_indexes(self, tmp_path: Path) -> None:
        content = """\
scoring:
  templates:
    dividend:
      factors:
        - { field: "pe_percentile_5y", weight: 1.0 }
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3
score_ranges:
  - max_percentile: 100
    score: 9
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key_env: "TEST_API_KEY"
  base_url: ""
  timeout: 30
report:
  show_detail: true
  sort_by: "score"
"""
        p = _write_yaml(tmp_path, "config.yaml", content)
        with pytest.raises(ConfigError, match="缺少必要字段"):
            load_config(p)

    def test_missing_scoring_templates(self, tmp_path: Path) -> None:
        content = """\
indexes:
  - code: "000922"
    name: "test"
    market: "CN"
    template: "dividend"
scoring:
  pe_percentile_years: 5
  dividend_yield_percentile_years: 5
  price_position_years: 3
score_ranges:
  - max_percentile: 100
    score: 9
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key_env: "TEST_API_KEY"
  base_url: ""
  timeout: 30
report:
  show_detail: true
  sort_by: "score"
"""
        p = _write_yaml(tmp_path, "config.yaml", content)
        with pytest.raises(ConfigError, match="格式错误|缺少必要字段"):
            load_config(p)
