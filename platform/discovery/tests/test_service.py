from discovery.config import Config
from discovery.service import DiscoveryController


def config(tmp_path):
    return Config(
        artifacts_dir=tmp_path / "artifacts",
        output_dir=tmp_path / "output",
        interval=120,
        fetch_timeout=5,
        socket_path="/sock",
        mesh_config_path=tmp_path / "mesh.json",
        management_api_token="secret",
    )


def test_trigger_coalesces_repeated_pending_requests(tmp_path):
    controller = DiscoveryController(config(tmp_path), runner=lambda cfg: [])

    assert controller.trigger() is True
    assert controller.trigger() is False


def test_pending_pass_records_safe_discovered_peer_summaries(tmp_path):
    discovered = [{"hostname": "pi", "dns_name": "pi.tail1234.ts.net", "online": True}]
    controller = DiscoveryController(config(tmp_path), runner=lambda cfg: discovered)
    controller.trigger()

    assert controller.run_pending_once() is True
    assert controller.discovered_peers() == discovered
    assert controller.run_pending_once() is False


def test_discovered_peer_snapshot_cannot_mutate_controller_state(tmp_path):
    controller = DiscoveryController(
        config(tmp_path),
        runner=lambda cfg: [{"hostname": "pi", "dns_name": "pi.tail1234.ts.net", "online": True}],
    )
    controller.trigger()
    controller.run_pending_once()

    snapshot = controller.discovered_peers()
    snapshot.clear()

    assert controller.discovered_peers()[0]["hostname"] == "pi"
