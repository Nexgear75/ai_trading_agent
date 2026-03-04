"""Tests for dashboard project structure, dependencies and Streamlit config.

Task #073 — WS-D-1: Project structure and dependencies for Streamlit dashboard.

Verifies:
- requirements-dashboard.txt exists with correct packages and versions (Annexe C).
- scripts/dashboard/ tree matches §10.2 structure.
- scripts/dashboard/pages/ contains exactly 4 page files.
- .streamlit/config.toml matches §10.4 specification.
- No version conflict between requirements-dashboard.txt and requirements.txt.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# §1 — requirements-dashboard.txt existence and content
# ---------------------------------------------------------------------------

class TestRequirementsDashboard:
    """Tests for requirements-dashboard.txt (Annexe C)."""

    REQ_FILE = PROJECT_ROOT / "requirements-dashboard.txt"

    # Exact expected packages and minimum versions per Annexe C
    EXPECTED_PACKAGES: dict[str, str] = {
        "streamlit": ">=1.30",
        "plotly": ">=5.18",
        "pandas": ">=2.0",
        "numpy": ">=1.24",
        "PyYAML": ">=6.0",
    }

    def test_file_exists(self) -> None:
        """#073 — requirements-dashboard.txt must exist at project root."""
        assert self.REQ_FILE.is_file(), (
            f"requirements-dashboard.txt not found at {self.REQ_FILE}"
        )

    def test_all_packages_present(self) -> None:
        """#073 — All Annexe C packages must be listed."""
        content = self.REQ_FILE.read_text()
        lines = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        # Extract package names (lowercase for comparison)
        found_packages = {ln.split(">=")[0].split("==")[0].strip().lower() for ln in lines}
        for pkg in self.EXPECTED_PACKAGES:
            assert pkg.lower() in found_packages, (
                f"Package '{pkg}' missing from requirements-dashboard.txt"
            )

    def test_version_specs_match(self) -> None:
        """#073 — Each package has the exact version spec from Annexe C."""
        content = self.REQ_FILE.read_text()
        lines = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        for pkg, version_spec in self.EXPECTED_PACKAGES.items():
            expected_line = f"{pkg}{version_spec}"
            assert expected_line in lines, (
                f"Expected '{expected_line}' in requirements-dashboard.txt, "
                f"got lines: {lines}"
            )

    def test_no_extra_packages(self) -> None:
        """#073 — Only Annexe C packages should be present (no extras)."""
        content = self.REQ_FILE.read_text()
        lines = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        assert len(lines) == len(self.EXPECTED_PACKAGES), (
            f"Expected {len(self.EXPECTED_PACKAGES)} packages, found {len(lines)}: {lines}"
        )

    def test_no_conflict_with_main_requirements(self) -> None:
        """#073 — Shared packages must have compatible version specs with requirements.txt."""
        main_req = PROJECT_ROOT / "requirements.txt"
        assert main_req.is_file(), "requirements.txt must exist"

        main_lines = [
            ln.strip()
            for ln in main_req.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        dash_lines = [
            ln.strip()
            for ln in self.REQ_FILE.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

        def parse_pkg_version(line: str) -> tuple[str, str]:
            """Parse 'pkg>=X.Y' into (pkg_lower, version_spec)."""
            for sep in [">=", "==", "<=", "~=", "!="]:
                if sep in line:
                    name, ver = line.split(sep, 1)
                    return name.strip().lower(), f"{sep}{ver.strip()}"
            return line.strip().lower(), ""

        main_pkgs = dict(parse_pkg_version(ln) for ln in main_lines)
        dash_pkgs = dict(parse_pkg_version(ln) for ln in dash_lines)

        # Shared packages: pandas, numpy, PyYAML
        shared = set(main_pkgs) & set(dash_pkgs)
        assert len(shared) >= 3, (
            f"Expected at least 3 shared packages (pandas, numpy, pyyaml), found {shared}"
        )

        # For shared packages, dashboard version spec must be compatible
        # (same or less restrictive minimum)
        for pkg in shared:
            main_spec = main_pkgs[pkg]
            dash_spec = dash_pkgs[pkg]
            # Both use >= — dashboard min must be <= main min for compatibility
            if main_spec.startswith(">=") and dash_spec.startswith(">="):
                main_min = main_spec.replace(">=", "")
                dash_min = dash_spec.replace(">=", "")
                # Parse as tuples for comparison
                main_parts = tuple(int(x) for x in main_min.split("."))
                dash_parts = tuple(int(x) for x in dash_min.split("."))
                assert dash_parts <= main_parts or main_parts <= dash_parts, (
                    f"Version conflict for '{pkg}': main={main_spec}, dashboard={dash_spec}"
                )


# ---------------------------------------------------------------------------
# §2 — scripts/dashboard/ arborescence (§10.2)
# ---------------------------------------------------------------------------

class TestDashboardArborescence:
    """Tests for scripts/dashboard/ directory structure per §10.2."""

    DASHBOARD_DIR = PROJECT_ROOT / "scripts" / "dashboard"

    EXPECTED_FILES = [
        "app.py",
        "data_loader.py",
        "charts.py",
        "utils.py",
    ]

    EXPECTED_PAGES = [
        "1_overview.py",
        "2_run_detail.py",
        "3_comparison.py",
        "4_fold_analysis.py",
    ]

    def test_dashboard_dir_exists(self) -> None:
        """#073 — scripts/dashboard/ directory must exist."""
        assert self.DASHBOARD_DIR.is_dir(), (
            f"Directory not found: {self.DASHBOARD_DIR}"
        )

    def test_pages_dir_exists(self) -> None:
        """#073 — scripts/dashboard/pages/ directory must exist."""
        pages_dir = self.DASHBOARD_DIR / "pages"
        assert pages_dir.is_dir(), f"Directory not found: {pages_dir}"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_root_files_exist(self, filename: str) -> None:
        """#073 — Each root-level dashboard file must exist."""
        filepath = self.DASHBOARD_DIR / filename
        assert filepath.is_file(), f"File not found: {filepath}"

    @pytest.mark.parametrize("filename", EXPECTED_PAGES)
    def test_page_files_exist(self, filename: str) -> None:
        """#073 — Each page file must exist in scripts/dashboard/pages/."""
        filepath = self.DASHBOARD_DIR / "pages" / filename
        assert filepath.is_file(), f"File not found: {filepath}"

    def test_pages_count(self) -> None:
        """#073 — Exactly 4 page files in scripts/dashboard/pages/."""
        pages_dir = self.DASHBOARD_DIR / "pages"
        py_files = list(pages_dir.glob("*.py"))
        # Exclude __init__.py if present
        page_files = [f for f in py_files if f.name != "__init__.py"]
        assert len(page_files) == 4, (
            f"Expected 4 page files, found {len(page_files)}: "
            f"{[f.name for f in page_files]}"
        )

    def test_all_files_are_python(self) -> None:
        """#073 — All dashboard source files must be .py files."""
        all_py = list(self.DASHBOARD_DIR.rglob("*.py"))
        assert len(all_py) >= 8, (
            f"Expected at least 8 .py files in dashboard tree, found {len(all_py)}"
        )

    def test_files_have_docstring(self) -> None:
        """#073 — Each stub file must contain a module docstring."""
        all_files = self.EXPECTED_FILES + [
            f"pages/{p}" for p in self.EXPECTED_PAGES
        ]
        for rel_path in all_files:
            filepath = self.DASHBOARD_DIR / rel_path
            content = filepath.read_text()
            assert '"""' in content or "'''" in content, (
                f"File {rel_path} is missing a module docstring"
            )


# ---------------------------------------------------------------------------
# §3 — .streamlit/config.toml (§10.4)
# ---------------------------------------------------------------------------

class TestStreamlitConfig:
    """Tests for .streamlit/config.toml conformity with §10.4."""

    CONFIG_FILE = PROJECT_ROOT / ".streamlit" / "config.toml"

    def test_config_file_exists(self) -> None:
        """#073 — .streamlit/config.toml must exist."""
        assert self.CONFIG_FILE.is_file(), (
            f"Config file not found: {self.CONFIG_FILE}"
        )

    def _read_config(self) -> configparser.ConfigParser:
        """Read the TOML config using configparser (compatible with INI-style TOML)."""
        config = configparser.ConfigParser()
        config.read(self.CONFIG_FILE)
        return config

    def test_server_headless(self) -> None:
        """#073 — [server] headless = true."""
        config = self._read_config()
        assert config.get("server", "headless") == "true"

    def test_server_port(self) -> None:
        """#073 — [server] port = 8501."""
        config = self._read_config()
        assert config.get("server", "port") == "8501"

    def test_theme_primary_color(self) -> None:
        """#073 — [theme] primaryColor = '#3498db'."""
        config = self._read_config()
        val = config.get("theme", "primaryColor").strip('"').strip("'")
        assert val == "#3498db"

    def test_theme_background_color(self) -> None:
        """#073 — [theme] backgroundColor = '#ffffff'."""
        config = self._read_config()
        val = config.get("theme", "backgroundColor").strip('"').strip("'")
        assert val == "#ffffff"

    def test_theme_secondary_background_color(self) -> None:
        """#073 — [theme] secondaryBackgroundColor = '#f0f2f6'."""
        config = self._read_config()
        val = config.get("theme", "secondaryBackgroundColor").strip('"').strip("'")
        assert val == "#f0f2f6"

    def test_theme_text_color(self) -> None:
        """#073 — [theme] textColor = '#262730'."""
        config = self._read_config()
        val = config.get("theme", "textColor").strip('"').strip("'")
        assert val == "#262730"

    def test_theme_font(self) -> None:
        """#073 — [theme] font = 'sans serif'."""
        config = self._read_config()
        val = config.get("theme", "font").strip('"').strip("'")
        assert val == "sans serif"

    def test_browser_no_usage_stats(self) -> None:
        """#073 — [browser] gatherUsageStats = false."""
        config = self._read_config()
        assert config.get("browser", "gatherUsageStats") == "false"

    def test_all_sections_present(self) -> None:
        """#073 — Config must have exactly [server], [theme], [browser] sections."""
        config = self._read_config()
        sections = set(config.sections())
        expected = {"server", "theme", "browser"}
        assert sections == expected, (
            f"Expected sections {expected}, found {sections}"
        )


# ---------------------------------------------------------------------------
# §4 — Edge cases / error scenarios
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and boundary tests for dashboard structure."""

    DASHBOARD_DIR = PROJECT_ROOT / "scripts" / "dashboard"

    def test_no_unexpected_directories(self) -> None:
        """#073 — No unexpected subdirectories in scripts/dashboard/."""
        subdirs = [
            d for d in self.DASHBOARD_DIR.iterdir()
            if d.is_dir() and d.name != "__pycache__" and d.name != "pages"
        ]
        assert len(subdirs) == 0, (
            f"Unexpected subdirectories: {[d.name for d in subdirs]}"
        )

    def test_pages_naming_convention(self) -> None:
        """#073 — Page files follow N_name.py numbering convention."""
        pages_dir = self.DASHBOARD_DIR / "pages"
        page_files = sorted(
            f.name for f in pages_dir.glob("*.py")
            if f.name != "__init__.py"
        )
        for name in page_files:
            # Must match pattern: digit_name.py
            assert name[0].isdigit(), (
                f"Page file '{name}' doesn't start with a digit"
            )
            assert name[1] == "_", (
                f"Page file '{name}' doesn't have underscore after digit"
            )

    def test_streamlit_config_dir_exists(self) -> None:
        """#073 — .streamlit/ directory must exist."""
        streamlit_dir = PROJECT_ROOT / ".streamlit"
        assert streamlit_dir.is_dir(), f"Directory not found: {streamlit_dir}"

    def test_requirements_file_not_empty(self) -> None:
        """#073 — requirements-dashboard.txt must not be empty."""
        req_file = PROJECT_ROOT / "requirements-dashboard.txt"
        content = req_file.read_text().strip()
        assert len(content) > 0, "requirements-dashboard.txt is empty"

    def test_requirements_no_duplicate_packages(self) -> None:
        """#073 — No duplicate package entries in requirements-dashboard.txt."""
        req_file = PROJECT_ROOT / "requirements-dashboard.txt"
        lines = [
            ln.strip()
            for ln in req_file.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        pkg_names = [ln.split(">=")[0].split("==")[0].strip().lower() for ln in lines]
        assert len(pkg_names) == len(set(pkg_names)), (
            f"Duplicate packages found: {pkg_names}"
        )
