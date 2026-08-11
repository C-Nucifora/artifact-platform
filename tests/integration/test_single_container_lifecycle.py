import subprocess


COMPOSE = ["docker", "compose", "-f", "docker-compose.single.test.yml"]


def run(*args):
    return subprocess.run(
        [*COMPOSE, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_sigterm_stops_the_container_successfully():
    container_id = run("ps", "-q", "artifact-platform")
    assert container_id

    subprocess.run(
        ["docker", "kill", "--signal", "TERM", container_id],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["docker", "wait", container_id],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "0"
