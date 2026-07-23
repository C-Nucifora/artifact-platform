"""Tests for manifest building from an artifacts/ tree."""

import json

import pytest

from discovery.manifest import build_manifest


@pytest.fixture
def artifacts(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    return root


def make_artifact(root, slug, meta=None, meta_raw=None, with_index=True):
    d = root / slug
    d.mkdir()
    if with_index:
        (d / "index.html").write_text("<h1>hi</h1>")
    if meta_raw is not None:
        (d / "meta.json").write_text(meta_raw)
    elif meta is not None:
        (d / "meta.json").write_text(json.dumps(meta))
    return d


def slugs(manifest):
    return [a["slug"] for a in manifest["artifacts"]]


def test_empty_dir_yields_empty_artifacts(artifacts):
    m = build_manifest(artifacts)
    assert m["artifacts"] == []


def test_nonexistent_dir_yields_empty_artifacts(tmp_path):
    m = build_manifest(tmp_path / "does-not-exist")
    assert m["artifacts"] == []


def test_full_meta_json(artifacts):
    make_artifact(artifacts, "clock", meta={"title": "World Clock", "description": "Times."})
    m = build_manifest(artifacts)
    assert m["artifacts"] == [
        {
            "slug": "clock",
            "title": "World Clock",
            "description": "Times.",
            "path": "/artifacts/clock/",
        }
    ]


def test_missing_meta_json_falls_back_to_slug(artifacts):
    make_artifact(artifacts, "my-tool")
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "my-tool"
    assert entry["description"] == ""


def test_meta_missing_title_falls_back_to_slug(artifacts):
    make_artifact(artifacts, "gizmo", meta={"description": "A gizmo."})
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "gizmo"
    assert entry["description"] == "A gizmo."


def test_meta_missing_description_falls_back_to_empty(artifacts):
    make_artifact(artifacts, "gizmo", meta={"title": "Gizmo"})
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "Gizmo"
    assert entry["description"] == ""


def test_malformed_meta_json_falls_back(artifacts):
    make_artifact(artifacts, "broken", meta_raw="{not json at all")
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "broken"
    assert entry["description"] == ""


def test_meta_json_not_an_object_falls_back(artifacts):
    make_artifact(artifacts, "listy", meta_raw='["a", "b"]')
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "listy"


def test_non_string_title_falls_back(artifacts):
    make_artifact(artifacts, "numeric", meta={"title": 42, "description": ["x"]})
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry["title"] == "numeric"
    assert entry["description"] == ""


def test_extra_meta_keys_ignored(artifacts):
    make_artifact(artifacts, "extra", meta={"title": "T", "description": "D", "color": "red"})
    (entry,) = build_manifest(artifacts)["artifacts"]
    assert entry == {"slug": "extra", "title": "T", "description": "D", "path": "/artifacts/extra/"}


def test_loose_files_ignored(artifacts):
    (artifacts / "README.txt").write_text("not an artifact")
    make_artifact(artifacts, "real")
    assert slugs(build_manifest(artifacts)) == ["real"]


def test_hidden_dirs_ignored(artifacts):
    hidden = artifacts / ".hidden"
    hidden.mkdir()
    (hidden / "index.html").write_text("x")
    make_artifact(artifacts, "visible")
    assert slugs(build_manifest(artifacts)) == ["visible"]


def test_sorted_by_slug(artifacts):
    for slug in ["zeta", "alpha", "mid"]:
        make_artifact(artifacts, slug)
    assert slugs(build_manifest(artifacts)) == ["alpha", "mid", "zeta"]


def test_device_info_included(artifacts):
    device = {"hostname": "studio", "dns_name": "studio.tail1234.ts.net"}
    m = build_manifest(artifacts, device=device)
    assert m["device"] == device


def test_device_defaults_to_empty_object(artifacts):
    assert build_manifest(artifacts)["device"] == {}


def test_manifest_has_version(artifacts):
    assert build_manifest(artifacts)["version"] == 1
