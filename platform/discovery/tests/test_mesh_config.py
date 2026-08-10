import json

import pytest

from discovery.mesh_config import (
    ConfigValidationError,
    RevisionConflict,
    load_mesh_config,
    parse_mesh_config,
    save_mesh_config,
)


def test_empty_document_normalizes_to_empty_mesh():
    document = parse_mesh_config({"version": 1})

    assert document.config.version == 1
    assert document.config.excluded_peers == ()
    assert document.config.peers == {}
    assert len(document.revision) == 64


def test_revision_is_stable_for_equivalent_key_order():
    first = parse_mesh_config(
        {
            "version": 1,
            "excluded_peers": ["pi.tail1234.ts.net"],
            "peers": {"pi.tail1234.ts.net": {"public_url": "https://pi.example.com"}},
        }
    )
    second = parse_mesh_config(
        {
            "peers": {"pi.tail1234.ts.net": {"public_url": "https://pi.example.com"}},
            "excluded_peers": ["pi.tail1234.ts.net"],
            "version": 1,
        }
    )

    assert first.revision == second.revision


@pytest.mark.parametrize(
    "raw",
    [
        {"version": 2},
        {"version": 1, "unexpected": True},
        {"version": 1, "excluded_peers": ["not a host"]},
        {"version": 1, "peers": {"bad peer": {}}},
        {"version": 1, "peers": {"pi": {"ssh_target": "root@pi"}}},
        {"version": 1, "peers": {"pi": {"public_url": "http://pi.example.com"}}},
        {"version": 1, "peers": {"pi": {"excluded_artifacts": ["../secret"]}}},
        {"version": 1, "peers": {"pi": {"unknown": "value"}}},
    ],
)
def test_invalid_document_is_rejected(raw):
    with pytest.raises(ConfigValidationError):
        parse_mesh_config(raw)


def test_peer_rule_normalizes_all_supported_fields():
    document = parse_mesh_config(
        {
            "version": 1,
            "peers": {
                "manual-node": {
                    "manual": True,
                    "ssh_target": "manual-node.tail1234.ts.net",
                    "public_url": "https://manual.example.com/catalog",
                    "excluded_artifacts": ["private-demo", "internal"],
                }
            },
        }
    )

    rule = document.config.peers["manual-node"]
    assert rule.manual is True
    assert rule.ssh_target == "manual-node.tail1234.ts.net"
    assert rule.public_url == "https://manual.example.com/catalog"
    assert rule.excluded_artifacts == ("internal", "private-demo")


def test_manual_peer_requires_both_endpoints():
    with pytest.raises(ConfigValidationError):
        parse_mesh_config({"version": 1, "peers": {"workshop": {"manual": True}}})


def test_load_missing_file_returns_empty_configuration(tmp_path):
    document = load_mesh_config(tmp_path / "missing.json")

    assert document.config.version == 1
    assert document.config.peers == {}


def test_load_invalid_file_uses_last_valid_document(tmp_path):
    path = tmp_path / "mesh.json"
    saved = save_mesh_config(
        path,
        parse_mesh_config({"version": 1, "excluded_peers": ["pi.tail1234.ts.net"]}),
        None,
    )
    path.write_text("{broken", encoding="utf-8")

    loaded = load_mesh_config(path, fallback=saved)

    assert loaded == saved


def test_save_rejects_stale_revision_without_changing_file(tmp_path):
    path = tmp_path / "mesh.json"
    first = save_mesh_config(path, parse_mesh_config({"version": 1}), None)
    replacement = parse_mesh_config({"version": 1, "excluded_peers": ["pi.tail1234.ts.net"]})

    with pytest.raises(RevisionConflict):
        save_mesh_config(path, replacement, "stale")

    assert load_mesh_config(path).revision == first.revision


def test_save_replaces_file_with_canonical_json(tmp_path):
    path = tmp_path / "mesh.json"
    first = save_mesh_config(path, parse_mesh_config({"version": 1}), None)
    replacement = parse_mesh_config(
        {
            "version": 1,
            "excluded_peers": ["pi.tail1234.ts.net"],
            "peers": {},
        }
    )

    saved = save_mesh_config(path, replacement, first.revision)

    assert saved.revision == replacement.revision
    assert json.loads(path.read_text(encoding="utf-8"))["excluded_peers"] == ["pi.tail1234.ts.net"]
    assert not list(tmp_path.glob("*.tmp"))
