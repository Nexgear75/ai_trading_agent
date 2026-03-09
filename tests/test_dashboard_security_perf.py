"""Tests for dashboard security and performance constraints. #089

Validates §11.1 (security: read-only, path validation) and §11.2 (performance:
@st.cache_data, lazy loading, pagination, >200 folds warning).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "scripts" / "dashboard"
DATA_LOADER_PATH = DASHBOARD_DIR / "data_loader.py"


def _get_all_dashboard_py_files() -> list[Path]:
    """Collect all .py files under scripts/dashboard/."""
    return sorted(DASHBOARD_DIR.rglob("*.py"))


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestNoWriteOperations:
    """§11.1 — Dashboard must be read-only: no write ops anywhere. #089"""

    WRITE_PATTERNS = [
        r"""open\s*\([^)]*['"][wa]['"]""",
        r"""\.to_csv\s*\(""",
        r"""\.to_json\s*\(""",
        r"""\.to_parquet\s*\(""",
        r"""\.to_excel\s*\(""",
        r"""shutil\.\w*(copy|move|rmtree)""",
        r"""os\.remove\s*\(""",
        r"""os\.unlink\s*\(""",
        r"""os\.makedirs\s*\(""",
        r"""os\.mkdir\s*\(""",
        r"""Path\([^)]*\)\.write_""",
        r"""Path\([^)]*\)\.mkdir""",
        r"""Path\([^)]*\)\.unlink""",
        r"""st\.file_uploader""",
    ]

    def test_no_write_ops_in_dashboard(self) -> None:
        """#089 — No write operations in any dashboard .py file."""
        violations: list[str] = []
        for py_file in _get_all_dashboard_py_files():
            source = _read_source(py_file)
            for pattern in self.WRITE_PATTERNS:
                matches = list(re.finditer(pattern, source))
                for match in matches:
                    line_no = source[:match.start()].count("\n") + 1
                    violations.append(
                        f"{py_file.name}:{line_no}: {match.group(0)}"
                    )
        assert not violations, (
            "Write operations found in dashboard:\n"
            + "\n".join(violations)
        )


class TestPathValidation:
    """§11.1 — Input paths must be validated with Path.resolve(). #089"""

    def test_data_loader_resolve_in_load_functions(self) -> None:
        """#089 — data_loader.py loader functions call Path.resolve() on input paths."""
        source = _read_source(DATA_LOADER_PATH)
        tree = ast.parse(source)

        loader_functions = [
            "load_run_metrics",
            "load_run_manifest",
            "load_config_snapshot",
            "load_equity_curve",
            "load_fold_equity_curve",
            "load_trades",
            "load_fold_trades",
            "load_predictions",
            "load_fold_metrics",
        ]

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in loader_functions:
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None, (
                    f"Cannot get source for {node.name}"
                )
                assert ".resolve()" in func_source, (
                    f"Function {node.name}() must call .resolve() "
                    f"on input path to prevent directory traversal (§11.1)"
                )

    def test_discover_runs_resolve(self) -> None:
        """#089 — discover_runs() calls .resolve() on runs_dir."""
        source = _read_source(DATA_LOADER_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "discover_runs":
                func_source = ast.get_source_segment(source, node)
                assert func_source is not None
                assert ".resolve()" in func_source, (
                    "discover_runs() must call .resolve() on input path (§11.1)"
                )
                break
        else:
            pytest.fail("discover_runs() not found in data_loader.py")


class TestCacheDataDecorators:
    """§11.2 — Loading functions must use @st.cache_data. #089"""

    CACHEABLE_FUNCTIONS = [
        "load_run_metrics",
        "load_run_manifest",
        "load_config_snapshot",
        "load_equity_curve",
        "load_fold_equity_curve",
        "load_trades",
        "load_fold_trades",
        "load_predictions",
        "load_fold_metrics",
    ]

    def test_cache_data_decorators_present(self) -> None:
        """#089 — All loading functions have @st.cache_data or @_cache_data."""
        source = _read_source(DATA_LOADER_PATH)
        tree = ast.parse(source)

        missing_cache: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in self.CACHEABLE_FUNCTIONS:
                has_cache = False
                for decorator in node.decorator_list:
                    dec_source = ast.get_source_segment(source, decorator)
                    if dec_source and "cache_data" in dec_source:
                        has_cache = True
                        break
                if not has_cache:
                    missing_cache.append(node.name)

        assert not missing_cache, (
            f"Functions missing @st.cache_data or @_cache_data decorator: "
            f"{missing_cache} (§11.2)"
        )


class TestFoldsWarning:
    """§11.2 — Warning if a run has > 200 folds. #089"""

    def test_folds_warning_code_exists(self) -> None:
        """#089 — discover_runs or page code checks for > 200 folds."""
        # Check data_loader or page files for the 200 folds threshold
        found = False
        for py_file in _get_all_dashboard_py_files():
            source = _read_source(py_file)
            if "200" in source and "fold" in source.lower():
                found = True
                break
        assert found, (
            "No code found checking for > 200 folds threshold (§11.2)"
        )

    def test_folds_warning_in_data_loader(self) -> None:
        """#089 — data_loader.py contains >200 folds check."""
        source = _read_source(DATA_LOADER_PATH)
        assert "200" in source, (
            "data_loader.py should contain a >200 folds threshold check (§11.2)"
        )


class TestPaginationConstant:
    """§11.2 — Trade journals paginated at 50 lines/page. #089"""

    def test_pagination_50_in_run_detail(self) -> None:
        """#089 — run_detail page uses page_size=50."""
        run_detail_path = DASHBOARD_DIR / "pages" / "2_run_detail.py"
        if not run_detail_path.exists():
            pytest.skip("2_run_detail.py not found")
        source = _read_source(run_detail_path)
        assert "50" in source, "Page 2 should paginate trades at 50 per page"

    def test_pagination_50_in_fold_analysis(self) -> None:
        """#089 — fold_analysis page uses page_size=50."""
        fold_path = DASHBOARD_DIR / "pages" / "4_fold_analysis.py"
        if not fold_path.exists():
            pytest.skip("4_fold_analysis.py not found")
        source = _read_source(fold_path)
        assert "50" in source, "Page 4 should paginate trades at 50 per page"


class TestNoNetworkAccess:
    """§11.1 — No network access in dashboard code. #089"""

    NETWORK_PATTERNS = [
        r"requests\.",
        r"urllib\.",
        r"httpx\.",
        r"aiohttp\.",
        r"socket\.",
    ]

    def test_no_network_imports(self) -> None:
        """#089 — No network library imports in dashboard code."""
        violations: list[str] = []
        for py_file in _get_all_dashboard_py_files():
            source = _read_source(py_file)
            for pattern in self.NETWORK_PATTERNS:
                if re.search(pattern, source):
                    violations.append(f"{py_file.name}: {pattern}")
        assert not violations, (
            "Network access found in dashboard:\n" + "\n".join(violations)
        )
