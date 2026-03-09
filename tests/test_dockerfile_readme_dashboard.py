"""Tests for Dockerfile.dashboard and README dashboard documentation.

Task #090 — WS-D-6: Dockerfile dashboard et documentation README.
Ref: Specification_Dashboard_Streamlit_v1.0.md §10.5, §10.3
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestDockerfileDashboard:
    """§10.5 — Dockerfile.dashboard conformity."""

    @pytest.fixture()
    def dockerfile_path(self) -> Path:
        return ROOT / "Dockerfile.dashboard"

    @pytest.fixture()
    def dockerfile_content(self, dockerfile_path: Path) -> str:
        assert dockerfile_path.exists(), "Dockerfile.dashboard must exist"
        return dockerfile_path.read_text()

    def test_dockerfile_exists(self, dockerfile_path: Path) -> None:
        """Dockerfile.dashboard file must exist at project root."""
        assert dockerfile_path.exists()

    def test_base_image_python311_slim(self, dockerfile_content: str) -> None:
        """Base image must be python:3.11-slim per §10.5."""
        assert "FROM python:3.11-slim" in dockerfile_content

    def test_workdir_app(self, dockerfile_content: str) -> None:
        """WORKDIR must be /app."""
        assert "WORKDIR /app" in dockerfile_content

    def test_expose_8501(self, dockerfile_content: str) -> None:
        """Port 8501 must be exposed."""
        assert "EXPOSE 8501" in dockerfile_content

    def test_headless_mode(self, dockerfile_content: str) -> None:
        """CMD must launch streamlit in headless mode."""
        assert "--server.headless=true" in dockerfile_content

    def test_streamlit_run_app(self, dockerfile_content: str) -> None:
        """CMD must run scripts/dashboard/app.py."""
        assert "scripts/dashboard/app.py" in dockerfile_content

    def test_requirements_copy_and_install(self, dockerfile_content: str) -> None:
        """Must COPY and pip install requirements-dashboard.txt."""
        assert "requirements-dashboard.txt" in dockerfile_content
        assert "pip install" in dockerfile_content

    def test_no_root_user(self, dockerfile_content: str) -> None:
        """Should not run as root — must have a USER directive or equivalent."""
        # Accept either USER directive or --chown in COPY
        has_user = "USER" in dockerfile_content and not dockerfile_content.strip().endswith(
            "USER root"
        )
        assert has_user, "Dockerfile.dashboard should not run as root"

    def test_distinct_from_pipeline_dockerfile(self) -> None:
        """Dockerfile.dashboard must be distinct from the pipeline Dockerfile."""
        pipeline = (ROOT / "Dockerfile").read_text()
        dashboard = (ROOT / "Dockerfile.dashboard").read_text()
        assert pipeline != dashboard


class TestReadmeDashboardSection:
    """README.md must contain a Dashboard section with complete instructions."""

    @pytest.fixture()
    def readme_content(self) -> str:
        readme_path = ROOT / "README.md"
        assert readme_path.exists()
        return readme_path.read_text()

    def test_dashboard_section_exists(self, readme_content: str) -> None:
        """README must contain a ## Dashboard section."""
        assert re.search(r"^## Dashboard", readme_content, re.MULTILINE)

    def test_install_dashboard_documented(self, readme_content: str) -> None:
        """README must document make install-dashboard."""
        assert "install-dashboard" in readme_content

    def test_make_dashboard_documented(self, readme_content: str) -> None:
        """README must document make dashboard command."""
        assert "make dashboard" in readme_content

    def test_cli_direct_launch_documented(self, readme_content: str) -> None:
        """README must document direct streamlit CLI launch."""
        assert "streamlit run" in readme_content

    def test_docker_launch_documented(self, readme_content: str) -> None:
        """README must document Docker launch for dashboard."""
        assert "Dockerfile.dashboard" in readme_content
        assert "docker build" in readme_content or "docker-dashboard" in readme_content

    def test_runs_dir_env_var_documented(self, readme_content: str) -> None:
        """README must mention AI_TRADING_RUNS_DIR environment variable."""
        assert "AI_TRADING_RUNS_DIR" in readme_content

    def test_runs_dir_override_documented(self, readme_content: str) -> None:
        """README must show RUNS_DIR= override."""
        assert "RUNS_DIR=" in readme_content

    def test_three_launch_modes(self, readme_content: str) -> None:
        """All 3 launch modes must be documented: Makefile, CLI, Docker."""
        assert "make dashboard" in readme_content
        assert "streamlit run" in readme_content
        assert "docker" in readme_content.lower()


class TestMakefileDockerDashboard:
    """Makefile must have docker-dashboard target."""

    @pytest.fixture()
    def makefile_content(self) -> str:
        return (ROOT / "Makefile").read_text()

    def test_docker_dashboard_target_exists(self, makefile_content: str) -> None:
        """Makefile must contain docker-dashboard target."""
        assert re.search(r"^docker-dashboard:", makefile_content, re.MULTILINE)

    def test_docker_dashboard_phony(self, makefile_content: str) -> None:
        """docker-dashboard must be declared .PHONY."""
        assert "docker-dashboard" in makefile_content
        phony_lines = [
            line for line in makefile_content.splitlines() if line.startswith(".PHONY:")
        ]
        found = any("docker-dashboard" in line for line in phony_lines)
        assert found, "docker-dashboard must be in .PHONY"

    def test_docker_dashboard_builds_image(self, makefile_content: str) -> None:
        """docker-dashboard target must build the dashboard Docker image."""
        assert "Dockerfile.dashboard" in makefile_content

    def test_docker_dashboard_help_comment(self, makefile_content: str) -> None:
        """docker-dashboard target must have a ## help comment."""
        match = re.search(r"^docker-dashboard:.*##", makefile_content, re.MULTILINE)
        assert match, "docker-dashboard must have a ## help comment"
