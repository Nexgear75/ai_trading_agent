"""Tests for the project Makefile. #053

Validates Makefile syntax, targets, variables, and help output
using dry-run (make -n) and parsing approaches.
"""

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"


@pytest.fixture()
def makefile_content() -> str:
    """Read the Makefile content."""
    if not MAKEFILE_PATH.exists():
        pytest.fail("Makefile does not exist at project root")
    return MAKEFILE_PATH.read_text(encoding="utf-8")


def _run_make(target: str, dry_run: bool = True) -> subprocess.CompletedProcess:
    """Run make with optional dry-run flag."""
    cmd = ["make", "-f", str(MAKEFILE_PATH)]
    if dry_run:
        cmd.append("-n")
    cmd.append(target)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=30,
    )


def _run_make_with_vars(
    target: str, variables: dict[str, str], dry_run: bool = True
) -> subprocess.CompletedProcess:
    """Run make with variable overrides."""
    cmd = ["make", "-f", str(MAKEFILE_PATH)]
    if dry_run:
        cmd.append("-n")
    for key, value in variables.items():
        cmd.append(f"{key}={value}")
    cmd.append(target)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=30,
    )


class TestMakefileSyntax:
    """Verify Makefile syntax is valid."""

    def test_makefile_exists(self) -> None:
        """#053 — Makefile exists at project root."""
        assert MAKEFILE_PATH.exists(), "Makefile must exist at project root"

    def test_makefile_syntax_valid(self) -> None:
        """#053 — Makefile has valid syntax (make -n help succeeds)."""
        result = _run_make("help")
        assert result.returncode == 0, (
            f"Makefile syntax error: {result.stderr}"
        )


class TestHelpTarget:
    """Verify make help lists expected targets."""

    def test_help_returns_success(self) -> None:
        """#053 — make help returns exit code 0."""
        result = _run_make("help", dry_run=False)
        assert result.returncode == 0

    def test_help_lists_main_targets(self) -> None:
        """#053 — make help output contains main targets."""
        result = _run_make("help", dry_run=False)
        output = result.stdout
        for target in ["install", "fetch-data", "qa", "run", "run-all"]:
            assert target in output, f"Target '{target}' missing from help output"

    def test_help_lists_utility_targets(self) -> None:
        """#053 — make help output contains utility targets."""
        result = _run_make("help", dry_run=False)
        output = result.stdout
        for target in ["test", "lint", "docker-build", "docker-run", "clean"]:
            assert target in output, f"Target '{target}' missing from help output"

    def test_help_lists_gate_targets(self) -> None:
        """#053 — make help output contains gate targets."""
        result = _run_make("help", dry_run=False)
        output = result.stdout
        for target in [
            "gate-m1", "gate-m2", "gate-m3", "gate-m4", "gate-m5", "gate-m6",
            "gate-features", "gate-split", "gate-backtest", "gate-doc",
            "gate-perf",
        ]:
            assert target in output, f"Target '{target}' missing from help output"


class TestVariableDefaults:
    """Verify overridable variables have correct defaults."""

    def test_config_default(self, makefile_content: str) -> None:
        """#053 — CONFIG variable defaults to configs/default.yaml."""
        assert "configs/default.yaml" in makefile_content

    def test_config_variable_defined(self, makefile_content: str) -> None:
        """#053 — CONFIG variable is defined with ?= (overridable)."""
        assert "CONFIG" in makefile_content
        # ?= means it can be overridden from command line
        lines = makefile_content.splitlines()
        config_lines = [ln for ln in lines if ln.startswith("CONFIG")]
        assert len(config_lines) >= 1, "CONFIG variable not defined at top level"
        assert any("?=" in ln for ln in config_lines), (
            "CONFIG should use ?= for overridability"
        )

    def test_model_variable_defined(self, makefile_content: str) -> None:
        """#053 — MODEL variable is defined (overridable)."""
        assert "MODEL" in makefile_content

    def test_seed_variable_defined(self, makefile_content: str) -> None:
        """#053 — SEED variable is defined (overridable)."""
        assert "SEED" in makefile_content


class TestMainTargetsDryRun:
    """Verify main targets produce correct commands in dry-run."""

    def test_install_target(self) -> None:
        """#053 — make install runs pip install -r requirements.txt."""
        result = _run_make("install")
        assert result.returncode == 0
        assert "pip install -r requirements.txt" in result.stdout

    def test_fetch_data_target(self) -> None:
        """#053 — make fetch-data runs ai_trading fetch with CONFIG."""
        result = _run_make("fetch-data")
        assert result.returncode == 0
        assert "python -m ai_trading fetch" in result.stdout
        assert "--config" in result.stdout

    def test_qa_target(self) -> None:
        """#053 — make qa runs ai_trading qa with CONFIG."""
        result = _run_make("qa")
        assert result.returncode == 0
        assert "python -m ai_trading qa" in result.stdout
        assert "--config" in result.stdout

    def test_run_target(self) -> None:
        """#053 — make run runs ai_trading run with CONFIG."""
        result = _run_make("run")
        assert result.returncode == 0
        assert "python -m ai_trading run" in result.stdout
        assert "--config" in result.stdout

    def test_run_all_target(self) -> None:
        """#053 — make run-all chains fetch-data, qa, run."""
        result = _run_make("run-all")
        assert result.returncode == 0
        output = result.stdout
        # run-all should trigger fetch-data, qa, and run commands
        assert "fetch" in output
        assert "qa" in output
        assert "run" in output


class TestUtilityTargetsDryRun:
    """Verify utility targets produce correct commands."""

    def test_test_target(self) -> None:
        """#053 — make test runs pytest tests/ -v."""
        result = _run_make("test")
        assert result.returncode == 0
        assert "pytest tests/ -v" in result.stdout

    def test_lint_target(self) -> None:
        """#053 — make lint runs ruff check and mypy."""
        result = _run_make("lint")
        assert result.returncode == 0
        assert "ruff check ai_trading/ tests/" in result.stdout
        assert "mypy ai_trading/" in result.stdout

    def test_docker_build_target(self) -> None:
        """#053 — make docker-build runs docker build."""
        result = _run_make("docker-build")
        assert result.returncode == 0
        assert "docker build" in result.stdout
        assert "ai-trading-pipeline" in result.stdout

    def test_docker_run_target(self) -> None:
        """#053 — make docker-run runs docker run with volume mounts."""
        result = _run_make("docker-run")
        assert result.returncode == 0
        output = result.stdout
        assert "docker run" in output
        assert "data" in output
        assert "runs" in output

    def test_clean_target(self) -> None:
        """#053 — make clean runs without error."""
        result = _run_make("clean")
        assert result.returncode == 0


class TestVariableOverrides:
    """Verify variables can be overridden."""

    def test_config_override(self) -> None:
        """#053 — CONFIG can be overridden on command line."""
        result = _run_make_with_vars(
            "run", {"CONFIG": "configs/custom.yaml"}
        )
        assert result.returncode == 0
        assert "configs/custom.yaml" in result.stdout

    def test_model_override_in_run(self) -> None:
        """#053 — MODEL override passes --set strategy.name to run."""
        result = _run_make_with_vars(
            "run", {"MODEL": "xgboost"}
        )
        assert result.returncode == 0
        output = result.stdout
        assert "--set" in output
        assert "strategy.name" in output
        assert "xgboost" in output

    def test_seed_override_in_run(self) -> None:
        """#053 — SEED override passes --set reproducibility.global_seed to run."""
        result = _run_make_with_vars(
            "run", {"SEED": "42"}
        )
        assert result.returncode == 0
        output = result.stdout
        assert "--set" in output
        assert "reproducibility.global_seed" in output
        assert "42" in output


class TestGateTargetsDryRun:
    """Verify gate targets produce correct commands."""

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
    def test_gate_milestone_targets(self, n: int) -> None:
        """#053 — make gate-m<N> runs without syntax error."""
        result = _run_make(f"gate-m{n}")
        assert result.returncode == 0, (
            f"gate-m{n} failed: {result.stderr}"
        )

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
    def test_gate_milestone_creates_reports_dir(self, n: int) -> None:
        """#053 — gate-m<N> dry-run mentions reports directory."""
        result = _run_make(f"gate-m{n}")
        assert "reports" in result.stdout, (
            f"gate-m{n} should create reports/ directory"
        )

    @pytest.mark.parametrize("gate", [
        "gate-features", "gate-split", "gate-backtest", "gate-doc", "gate-perf",
    ])
    def test_intra_milestone_gate_targets(self, gate: str) -> None:
        """#053 — intra-milestone gate targets run without error."""
        result = _run_make(gate)
        assert result.returncode == 0, (
            f"{gate} failed: {result.stderr}"
        )

    @pytest.mark.parametrize("gate", [
        "gate-features", "gate-split", "gate-backtest", "gate-doc",
    ])
    def test_intra_gate_has_coverage(self, gate: str) -> None:
        """#053 — intra-milestone gates include coverage check."""
        result = _run_make(gate)
        output = result.stdout
        assert "cov" in output.lower() or "--cov" in output, (
            f"{gate} should include coverage check"
        )


class TestGateDependencies:
    """Verify gate dependency chain in the Makefile content."""

    def test_gate_features_depends_on_gate_m1(self, makefile_content: str) -> None:
        """#053 — gate-features depends on gate-m1."""
        # Look for gate-features target with gate-m1 as prerequisite
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-features") and ":" in line:
                assert "gate-m1" in line, (
                    "gate-features should depend on gate-m1"
                )
                return
        pytest.fail("gate-features target not found in Makefile")

    def test_gate_split_depends_on_gate_features(self, makefile_content: str) -> None:
        """#053 — gate-split depends on gate-features."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-split") and ":" in line:
                assert "gate-features" in line, (
                    "gate-split should depend on gate-features"
                )
                return
        pytest.fail("gate-split target not found in Makefile")

    def test_gate_m2_depends_on_gate_split(self, makefile_content: str) -> None:
        """#053 — gate-m2 depends on gate-split."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-m2") and ":" in line:
                assert "gate-split" in line, (
                    "gate-m2 should depend on gate-split"
                )
                return
        pytest.fail("gate-m2 target not found in Makefile")

    def test_gate_doc_depends_on_gate_m2(self, makefile_content: str) -> None:
        """#053 — gate-doc depends on gate-m2."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-doc") and ":" in line:
                assert "gate-m2" in line, (
                    "gate-doc should depend on gate-m2"
                )
                return
        pytest.fail("gate-doc target not found in Makefile")

    def test_gate_m3_depends_on_gate_doc(self, makefile_content: str) -> None:
        """#053 — gate-m3 depends on gate-doc."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-m3") and ":" in line:
                assert "gate-doc" in line, (
                    "gate-m3 should depend on gate-doc"
                )
                return
        pytest.fail("gate-m3 target not found in Makefile")

    def test_gate_backtest_depends_on_gate_m3(self, makefile_content: str) -> None:
        """#053 — gate-backtest depends on gate-m3."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-backtest") and ":" in line:
                assert "gate-m3" in line, (
                    "gate-backtest should depend on gate-m3"
                )
                return
        pytest.fail("gate-backtest target not found in Makefile")

    def test_gate_m4_depends_on_gate_backtest(self, makefile_content: str) -> None:
        """#053 — gate-m4 depends on gate-backtest."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-m4") and ":" in line:
                assert "gate-backtest" in line, (
                    "gate-m4 should depend on gate-backtest"
                )
                return
        pytest.fail("gate-m4 target not found in Makefile")

    def test_gate_m5_depends_on_gate_m4(self, makefile_content: str) -> None:
        """#053 — gate-m5 depends on gate-m4."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-m5") and ":" in line:
                assert "gate-m4" in line, (
                    "gate-m5 should depend on gate-m4"
                )
                return
        pytest.fail("gate-m5 target not found in Makefile")

    def test_gate_m6_depends_on_gate_m5(self, makefile_content: str) -> None:
        """#058 — gate-m6 depends on gate-m5."""
        lines = makefile_content.splitlines()
        for line in lines:
            if line.startswith("gate-m6") and ":" in line:
                assert "gate-m5" in line, "gate-m6 should depend on gate-m5"
                return
        pytest.fail("gate-m6 target not found in Makefile")


class TestHelpComments:
    """Verify that ## comments exist for discoverable targets."""

    def test_all_main_targets_have_help_comments(self, makefile_content: str) -> None:
        """#053 — All main targets have ## help comments."""
        required_targets = [
            "install", "fetch-data", "qa", "run", "run-all",
            "test", "lint", "docker-build", "docker-run", "clean", "help",
        ]
        for target in required_targets:
            # Pattern: target-name: ... ## description
            found = False
            for line in makefile_content.splitlines():
                if line.startswith(target) and "##" in line:
                    found = True
                    break
            assert found, f"Target '{target}' missing ## help comment"

    def test_gate_targets_have_help_comments(self, makefile_content: str) -> None:
        """#053 — Gate targets have ## help comments."""
        gate_targets = [
            "gate-m1", "gate-m2", "gate-m3", "gate-m4", "gate-m5", "gate-m6",
            "gate-features", "gate-split", "gate-backtest", "gate-doc",
            "gate-perf",
        ]
        for target in gate_targets:
            found = False
            for line in makefile_content.splitlines():
                if line.startswith(target) and "##" in line:
                    found = True
                    break
            assert found, f"Gate target '{target}' missing ## help comment"

class TestGateM6:
    """Verify gate-m6 target specifics. #058"""

    def test_gate_m6_runs_fullscale_pytest(self) -> None:
        """#058 — gate-m6 runs pytest -m fullscale."""
        result = _run_make("gate-m6")
        assert result.returncode == 0
        assert "fullscale" in result.stdout
        assert "test_fullscale_btc" in result.stdout

    def test_gate_m6_creates_report(self) -> None:
        """#058 — gate-m6 creates gate_report_M6.json."""
        result = _run_make("gate-m6")
        assert result.returncode == 0
        assert "gate_report_M6" in result.stdout

    def test_gate_m6_chain_comment_includes_gm6(self, makefile_content: str) -> None:
        """#058 — Gate chain comment includes GM6."""
        found = False
        for line in makefile_content.splitlines():
            if "GM6" in line and line.strip().startswith("#"):
                found = True
                break
        assert found, "Gate chain comment should include GM6"

    def test_gate_m6_is_phony(self, makefile_content: str) -> None:
        """#058 — gate-m6 is declared .PHONY."""
        found = False
        for line in makefile_content.splitlines():
            if line.startswith(".PHONY") and "gate-m6" in line:
                found = True
                break
        assert found, "gate-m6 should be declared .PHONY"
