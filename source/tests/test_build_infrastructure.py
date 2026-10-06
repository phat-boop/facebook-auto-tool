"""Build configuration stays portable and test/build dependencies are declared."""
import runpy
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from packaging.requirements import Requirement
import configparser
import re


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"


def declared_requirements(path):
    requirements = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            requirements.update(declared_requirements(path.parent / line[3:].strip()))
        else:
            requirement = Requirement(line)
            requirements[requirement.name.lower().replace("_", "-")] = requirement
    return requirements


def test_build_manifest_includes_pinned_runtime_test_and_build_dependencies():
    requirements = declared_requirements(ROOT / "requirements-build.txt")
    for name in ("cryptography", "playwright", "openpyxl", "pytest", "pyinstaller"):
        assert name in requirements
    for requirement in requirements.values():
        specifiers = list(requirement.specifier)
        assert len(specifiers) == 1
        assert specifiers[0].operator == "=="
        assert "*" not in specifiers[0].version


def test_spec_uses_repository_inputs_even_outside_repository(monkeypatch, tmp_path):
    analysis = mock.Mock(return_value=SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[]))
    exe, pyz = mock.Mock(), mock.Mock()
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(ROOT / "client_app.spec"), init_globals={
        "SPECPATH": str(ROOT), "Analysis": analysis, "EXE": exe, "PYZ": pyz,
    })
    args, kwargs = analysis.call_args
    assert args[0] == [str(SOURCE / "client_app.py")]
    assert kwargs["pathex"] == [str(SOURCE)]
    assert kwargs["datas"] == [(str(SOURCE / "assets"), "assets"), (str(SOURCE / "picture.ico"), ".")]
    for source, _ in kwargs["datas"]:
        assert Path(source).exists()
    assert exe.call_args.kwargs["icon"] == [str(SOURCE / "picture.ico")]
    assert exe.call_args.kwargs["upx"] is False
    assert exe.call_args.kwargs["name"] == "client_app"
    assert exe.call_args.kwargs["console"] is False


def test_build_manifest_covers_resolved_transitive_dependencies():
    requirements = declared_requirements(ROOT / "requirements-build.txt")
    for name in requirements:
        for dependency in metadata.requires(name) or []:
            requirement = Requirement(dependency)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            assert requirement.name.lower().replace("_", "-") in requirements


def test_spec_is_allowed_while_generated_outputs_stay_ignored():
    patterns = [line.strip() for line in (ROOT / ".gitignore").read_text().splitlines()]
    assert "*.spec" in patterns
    assert "!/client_app.spec" in patterns
    assert patterns.index("!/client_app.spec") > patterns.index("*.spec")
    for pattern in ("build/", "dist/", ".venv-build/", ".pytest_cache/", "__pycache__/"):
        assert pattern in patterns
    assert "!/source/admin_key_gen.py" in patterns


def test_root_pytest_config_discovers_source_tests_and_modules():
    config = configparser.ConfigParser()
    config.read(ROOT / "pytest.ini", encoding="utf-8")
    assert config["pytest"]["testpaths"].split() == ["source/tests"]
    assert config["pytest"]["pythonpath"].split() == ["source"]
    assert SOURCE / "tests" == Path(__file__).resolve().parent
    assert not (ROOT / "client_app.py").exists()


def test_release_targets_source_but_keeps_metadata_and_outputs_at_root():
    text = (ROOT / "release.ps1").read_text(encoding="utf-8-sig")
    paths = {
        name: (parent, child) for name, parent, child in re.findall(
            r"(?m)^\$(\w+)\s*=\s*Join-Path\s+\$(\w+)\s+'([^']+)'", text)
    }
    assert paths["sourceRoot"] == ("projectRoot", "source")
    assert paths["clientPath"] == ("sourceRoot", "client_app.py")
    assert paths["versionJsonPath"] == ("projectRoot", "version.json")
    assert paths["specPath"] == ("projectRoot", "client_app.spec")
    assert paths["exePath"] == ("projectRoot", "dist\\client_app.exe")
