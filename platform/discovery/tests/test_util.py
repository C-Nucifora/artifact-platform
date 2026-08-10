"""Tests for atomic JSON writes."""

import json
import stat

from discovery.util import write_json_atomic


def test_writes_valid_json(tmp_path):
    target = tmp_path / "out.json"
    write_json_atomic(target, {"a": 1})
    assert json.loads(target.read_text()) == {"a": 1}


def test_overwrites_existing_file(tmp_path):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}')
    write_json_atomic(target, {"new": True})
    assert json.loads(target.read_text()) == {"new": True}


def test_no_temp_files_left_behind(tmp_path):
    target = tmp_path / "out.json"
    write_json_atomic(target, {"a": 1})
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


def test_output_ends_with_newline(tmp_path):
    target = tmp_path / "out.json"
    write_json_atomic(target, {"a": 1})
    assert target.read_text().endswith("\n")


def test_output_is_readable_by_the_unprivileged_ssh_user(tmp_path):
    target = tmp_path / "out.json"

    write_json_atomic(target, {"a": 1})

    assert stat.S_IMODE(target.stat().st_mode) == 0o644
