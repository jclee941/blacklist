from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import build_docs


def prepare_docs_root(root: Path, version: str = "1.2.3") -> Path:
    manual = root / "docs/manual"
    _ = manual.mkdir(parents=True)
    _ = (root / "VERSION").write_text(version, encoding="utf-8")
    for source_name, _output_name, _font_size, _margin in build_docs.DOC_SPECS:
        _ = (manual / source_name).write_text("# Guide\n\n저장소 루트 `VERSION` 기준\n", encoding="utf-8")
    return manual


def test_invalid_version_is_rejected_before_pandoc(tmp_path: Path) -> None:
    _ = prepare_docs_root(tmp_path, "1.2.3;touch PWNED")

    with pytest.raises(ValueError, match="invalid VERSION"):
        build_docs.build(tmp_path)

    assert not (tmp_path / "PWNED").exists()


def test_pdf_outputs_are_preserved_when_generation_fails(tmp_path: Path) -> None:
    manual = prepare_docs_root(tmp_path)
    outputs = [manual / output for _source, output, _font, _margin in build_docs.DOC_SPECS]
    for output in outputs:
        _ = output.write_bytes(b"existing")
    calls = 0

    def failing_runner(command: Sequence[str], _cwd: Path, _environment: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        _ = Path(command[-1]).write_bytes(b"new")
        if calls == 2:
            raise RuntimeError("pandoc failed")

    with pytest.raises(RuntimeError, match="pandoc failed"):
        build_docs.build(tmp_path, runner=failing_runner)

    assert [output.read_bytes() for output in outputs] == [b"existing", b"existing", b"existing"]


def test_successful_build_updates_all_outputs_and_freshness(tmp_path: Path) -> None:
    manual = prepare_docs_root(tmp_path)

    def successful_runner(command: Sequence[str], _cwd: Path, _environment: dict[str, str]) -> None:
        _ = Path(command[-1]).write_bytes(b"pdf")

    build_docs.build(tmp_path, runner=successful_runner)

    assert build_docs.check(tmp_path) is True
    _ = (manual / "blacklist-admin-guide.pdf").write_bytes(b"stale")
    assert build_docs.check(tmp_path) is False
    build_docs.build(tmp_path, runner=successful_runner)
    _ = (manual / "blacklist-user-guide.md").write_text("# Changed\n", encoding="utf-8")
    assert build_docs.check(tmp_path) is False


def test_fresh_build_is_regenerated_instead_of_trusting_the_marker(tmp_path: Path) -> None:
    _ = prepare_docs_root(tmp_path)
    calls = 0

    def successful_runner(command: Sequence[str], _cwd: Path, _environment: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        _ = Path(command[-1]).write_bytes(b"pdf")

    build_docs.build(tmp_path, runner=successful_runner)
    build_docs.build(tmp_path, runner=successful_runner)

    assert calls == len(build_docs.DOC_SPECS) * 2


def test_source_change_during_generation_preserves_existing_outputs(tmp_path: Path) -> None:
    manual = prepare_docs_root(tmp_path)
    outputs = [manual / output for _source, output, _font, _margin in build_docs.DOC_SPECS]
    for output in outputs:
        _ = output.write_bytes(b"existing")
    calls = 0

    def mutating_runner(command: Sequence[str], _cwd: Path, _environment: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        _ = Path(command[-1]).write_bytes(b"pdf")
        if calls == len(build_docs.DOC_SPECS):
            _ = (tmp_path / "VERSION").write_text("1.2.4\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="sources changed"):
        build_docs.build(tmp_path, runner=mutating_runner)

    assert [output.read_bytes() for output in outputs] == [b"existing", b"existing", b"existing"]


def test_transient_source_change_cannot_enter_published_pdf(tmp_path: Path) -> None:
    manual = prepare_docs_root(tmp_path)
    user_source = manual / "blacklist-user-guide.md"
    original = user_source.read_text(encoding="utf-8")
    calls = 0

    def transient_runner(command: Sequence[str], _cwd: Path, _environment: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        source = Path(command[1])
        _ = Path(command[-1]).write_bytes(source.read_bytes())
        if calls == 1:
            _ = user_source.write_text("# TRANSIENT-MUTATION\n", encoding="utf-8")
        elif calls == 2:
            _ = user_source.write_text(original, encoding="utf-8")

    build_docs.build(tmp_path, runner=transient_runner)

    assert b"TRANSIENT-MUTATION" not in (manual / "blacklist-user-guide.pdf").read_bytes()


def test_pandoc_contract_uses_a4_korean_fonts_and_blue_file_links() -> None:
    command = build_docs.pandoc_command(Path("source.md"), Path("output.pdf"), "10pt", "15mm", "1.2.3")
    joined = " ".join(command)

    assert "papersize=a4" in joined
    assert "CJKmainfont=NanumGothic" in joined
    assert "filecolor=blue" in joined
    assert "--sandbox" in command
    assert "--from=markdown-raw_tex-raw_attribute-yaml_metadata_block" in command
