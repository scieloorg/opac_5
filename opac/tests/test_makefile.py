# coding: utf-8
"""Dry-run coverage for Makefile recipes (does not execute side effects)."""

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every recipe target defined in the Makefile (alphabetical).
MAKEFILE_TARGETS = (
    "backup",
    "backup_sqlite",
    "build",
    "build_bundles",
    "build_i18n",
    "check-format",
    "check_js_deps",
    "check_perms",
    "clean_all_bundles",
    "clean_js_bundles",
    "clear",
    "clear_scheduler_tasks",
    "compile_messages",
    "coverage",
    "coverage_html",
    "create_catalog",
    "create_empty_sqlite",
    "create_superuser",
    "create_tables_dbsql",
    "docker_test",
    "down",
    "down_webapp",
    "exclude_opac_production",
    "fix_perms",
    "format",
    "gitclean",
    "help",
    "install_npm_deps",
    "invalidate_cache",
    "invalidate_cache_forced",
    "logs",
    "logs_tail",
    "make_messages",
    "mongodb_backup",
    "opac_version",
    "ps",
    "pull_webapp",
    "release_docker_build",
    "release_docker_push",
    "release_docker_tag",
    "reset_dbsql",
    "restore",
    "rm",
    "scrub",
    "send_audit_log_emails",
    "setup_scheduler_tasks",
    "shell",
    "sort-imports",
    "stop",
    "sync_rss_feeds",
    "sync_rss_news",
    "sync_rss_press_releases",
    "test",
    "test_coverage",
    "up",
    "update",
    "update_catalog",
    "update_webapp",
    "venv",
)

# Fragments that must appear in `make -n <target>` stdout (alphabetical keys).
EXPECTED_FRAGMENTS = {
    "backup": ("mongodump", "opac.sqlite", "Backup completo"),
    "backup_sqlite": ("backups/sqlite", "opac.sqlite", "Backup do SQLite"),
    "build": ("-f docker-compose-dev.yml", "build"),
    "build_bundles": ("gulp",),
    "build_i18n": (
        "make make_messages && make update_catalog && make compile_messages",
    ),
    "check-format": ("black --check opac",),
    "check_js_deps": ("NodeJs version:", "npm version:", "Gulp.js version:"),
    "check_perms": ("Verificando permissões", "data_opac_prod"),
    "clean_all_bundles": (
        "scielo-article-standalone.js",
        "scielo-bundle.js",
        "arquivo JS e CSS removidos",
    ),
    "clean_js_bundles": ("scielo-article-standalone.js", "scielo-bundle.js"),
    "clear": ("*.pyc", "__pycache__", "rm -Rf venv"),
    "clear_scheduler_tasks": ("clear_scheduler_tasks",),
    "compile_messages": ("pybabel compile -d opac/webapp/translations",),
    "coverage": (
        'OPAC_CONFIG="config/templates/testing.template"',
        'FLASK_COVERAGE="1"',
        "OPAC_MONGODB_HOST=",
        "flask --app opac.app test",
    ),
    "coverage_html": ("coverage html", "HTML report:"),
    "create_catalog": ("pybabel init", "messages.pot", "-l en"),
    "create_empty_sqlite": ("create_empty_sqlite",),
    "create_superuser": ("create_superuser",),
    "create_tables_dbsql": ("create_tables_dbsql",),
    "docker_test": ("make test",),
    "down": ("-f docker-compose-dev.yml", "down"),
    "down_webapp": (
        "rm -s -f opac_webapp opac-rq-scheduler opac-rq-worker-1 opac-rq-worker-sync-external",
    ),
    "exclude_opac_production": ("infrascielo/opac_5", "docker"),
    "fix_perms": ("Ajustando permissões", "chown", "chmod"),
    "format": ("black opac",),
    "gitclean": ("git clean -X -f -d",),
    "help": ("grep", "# help", "sort -f"),
    "install_npm_deps": ("npm install",),
    "invalidate_cache": ("invalidate_cache",),
    "invalidate_cache_forced": ("invalidate_cache --force-clear",),
    "logs": ("logs -f",),
    "logs_tail": ("logs -f --tail=50",),
    "make_messages": ("pybabel extract", "messages.pot"),
    "mongodb_backup": ("mongodump", "--username=", "--db opac"),
    "opac_version": ("Version file:",),
    "ps": ("-f docker-compose-dev.yml", "ps"),
    "pull_webapp": ("pull opac_webapp",),
    "release_docker_build": ("docker build", "OPAC_WEBAPP_VERSION", "COMMIT"),
    "release_docker_push": ("docker push", "infrascielo/opac_5:"),
    "release_docker_tag": ("docker tag", ":latest"),
    "reset_dbsql": ("reset_dbsql",),
    "restore": ("RESTORE_DATE", "mongorestore", "opac.sqlite"),
    "rm": ("-f docker-compose-dev.yml", "rm -f"),
    "scrub": ("git clean -x -f -d",),
    "send_audit_log_emails": ("send_audit_log_emails",),
    "setup_scheduler_tasks": ("setup_scheduler_tasks",),
    "shell": ("exec opac_webapp sh",),
    "sort-imports": ("isort . --profile black",),
    "stop": ("-f docker-compose-dev.yml", "stop"),
    "sync_rss_feeds": ("sync_rss_feeds",),
    "sync_rss_news": ("sync_rss_news",),
    "sync_rss_press_releases": ("sync_rss_press_releases",),
    "test": (
        "pybabel extract",
        "pybabel compile",
        'OPAC_CONFIG="config/templates/testing.template"',
        "OPAC_MONGODB_HOST=",
        "flask --app opac.app test",
    ),
    "test_coverage": (
        'OPAC_CONFIG="config/templates/testing.template"',
        'FLASK_COVERAGE="1"',
        "flask --app opac.app test",
    ),
    "up": ("-f docker-compose-dev.yml", "up -d"),
    "update": ("mongodump", "stop", "infrascielo/opac_5", "up -d"),
    "update_catalog": ("pybabel update", "messages.pot"),
    "update_webapp": ("pull opac_webapp", "rm -s -f opac_webapp", "up -d"),
    "venv": ("python3.11 -m venv", "requirements.txt", "requirements.dev.txt"),
}

COMPOSE_RE = re.compile(r"docker(?:-compose| compose)")


def make_dry_run(*args):
    """Run ``make -n`` and return CompletedProcess (stdout + stderr)."""
    return subprocess.run(
        ["make", "-n", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def makefile_targets_from_file():
    """Parse recipe target names from the Makefile (ignore variable assignments)."""
    targets = set()
    assign_re = re.compile(r"^[a-zA-Z0-9_-]+\s*[+:?]?=")
    target_re = re.compile(r"^([a-zA-Z0-9_-]+)\s*:")
    for line in (REPO_ROOT / "Makefile").read_text(encoding="utf-8").splitlines():
        if assign_re.match(line):
            continue
        match = target_re.match(line)
        if match:
            targets.add(match.group(1))
    return targets


class MakefileRecipesTestCase(unittest.TestCase):
    """Assert each Makefile target expands to the expected commands."""

    def _assert_dry_run_ok(self, result, target):
        self.assertEqual(
            result.returncode,
            0,
            f"make -n {target} failed:\nstdout={result.stdout}\nstderr={result.stderr}",
        )

    def _assert_fragments(self, result, target, fragments):
        self._assert_dry_run_ok(result, target)
        combined = result.stdout + result.stderr
        for fragment in fragments:
            self.assertIn(
                fragment,
                combined,
                f"Target {target!r}: missing {fragment!r} in:\n{combined}",
            )

    def test_expected_fragments_cover_all_makefile_targets(self):
        from_file = makefile_targets_from_file()
        self.assertEqual(
            set(MAKEFILE_TARGETS),
            from_file,
            "MAKEFILE_TARGETS diverged from Makefile recipes",
        )
        self.assertEqual(
            set(EXPECTED_FRAGMENTS),
            set(MAKEFILE_TARGETS),
            "EXPECTED_FRAGMENTS must cover every Makefile target",
        )
        self.assertEqual(
            list(MAKEFILE_TARGETS),
            sorted(MAKEFILE_TARGETS, key=str.lower),
            "MAKEFILE_TARGETS must stay alphabetical",
        )

    def test_all_targets_dry_run_recipes(self):
        for target in MAKEFILE_TARGETS:
            with self.subTest(target=target):
                extra = []
                if target == "create_catalog":
                    extra = ["LANG=en"]
                result = make_dry_run(target, *extra)
                self._assert_fragments(
                    result, target, EXPECTED_FRAGMENTS[target]
                )

    def test_help_output_is_alphabetically_sorted(self):
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Skip title/blank lines; keep option lines (target - description).
        option_lines = [
            line
            for line in result.stdout.splitlines()
            if " - " in line and not line.startswith("Make ")
        ]
        self.assertGreater(len(option_lines), 10)
        # Use the same `sort -f` the Makefile help recipe uses (locale-aware).
        sorted_result = subprocess.run(
            ["sort", "-f"],
            input="\n".join(option_lines) + "\n",
            capture_output=True,
            text=True,
            check=True,
        )
        expected = [
            line for line in sorted_result.stdout.splitlines() if line
        ]
        self.assertEqual(
            option_lines,
            expected,
            "make help options must match `sort -f` order",
        )

    def test_invalid_compose_file_errors(self):
        result = make_dry_run("up", "compose=invalid.yml")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docker-compose inválido", result.stderr)

    def test_up_with_production_compose(self):
        result = make_dry_run("up", "compose=docker-compose.yml")
        self._assert_dry_run_ok(result, "up")
        self.assertIn("-f docker-compose.yml", result.stdout)
        self.assertIn("up -d", result.stdout)
        self.assertRegex(result.stdout, COMPOSE_RE)

    def test_reset_dbsql_force_delete(self):
        result = make_dry_run("reset_dbsql", "FORCE_DELETE=true")
        self._assert_fragments(
            result, "reset_dbsql", ("reset_dbsql --force-delete",)
        )

    def test_create_tables_dbsql_force_delete(self):
        result = make_dry_run("create_tables_dbsql", "FORCE_DELETE=true")
        self._assert_fragments(
            result, "create_tables_dbsql", ("create_tables_dbsql --force-delete",)
        )

    def test_setup_scheduler_tasks_with_cron_string(self):
        result = make_dry_run(
            "setup_scheduler_tasks", 'CRON_STRING=0 * * * *'
        )
        self._assert_fragments(
            result,
            "setup_scheduler_tasks",
            ('--cron_string "0 * * * *"',),
        )

    def test_restore_with_restore_date(self):
        result = make_dry_run("restore", "RESTORE_DATE=2024-01-01")
        # Dry-run keeps shell vars unevaluated (`$BACKUP_DATE`).
        self._assert_fragments(
            result,
            "restore",
            (
                "BACKUP_DATE=2024-01-01",
                "mongorestore",
                "/data_opac_dev/backups/$BACKUP_DATE",
            ),
        )

    def test_mongodb_backup_uses_dev_data_path_by_default(self):
        result = make_dry_run("mongodb_backup")
        self._assert_fragments(
            result, "mongodb_backup", ("/data_opac_dev/backups/",)
        )

    def test_mongodb_backup_uses_prod_data_path_with_prod_compose(self):
        result = make_dry_run(
            "mongodb_backup", "compose=docker-compose.yml"
        )
        self._assert_fragments(
            result, "mongodb_backup", ("/data_opac_prod/backups/",)
        )

    def test_makefile_includes_compose_specific_mongo_env_file(self):
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("MONGO_ENV_FILE = .envs/.production/.mongo", makefile)
        self.assertIn("MONGO_ENV_FILE = .envs/.development/.mongo", makefile)
        self.assertIn("-include $(MONGO_ENV_FILE)", makefile)


if __name__ == "__main__":
    unittest.main()
