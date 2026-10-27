import time

from openhost_test_harness import OpenhostStack


def test_app_serves_owner(stack: OpenhostStack) -> None:
    # The app is marked running once its health check passes; "/" can take a little longer to come up.
    deadline = time.monotonic() + 60
    while True:
        response = stack.owner_session.get(f"{stack.url}/", timeout=30)
        if response.status_code < 400 or time.monotonic() > deadline:
            break
        time.sleep(2)
    assert response.status_code < 400, (
        f"GET / returned {response.status_code}: {response.text[:500]}\n\napp logs:\n{stack.app_logs()[-5000:]}"
    )


def test_base_url_matches_app_url(stack: OpenhostStack) -> None:
    # The harness zone is `harness.localhost:<port>`: BASE_URL must be plain http, with that port once. The
    # integrations page prints the Fever endpoint from it. The first request may be spent on auth-proxy login.
    stack.owner_session.get(f"{stack.url}/", timeout=30)
    response = stack.owner_session.get(f"{stack.url}/integrations", timeout=30)
    assert response.status_code == 200, response.text[:500]
    assert f"<strong>{stack.url}/fever/</strong>" in response.text, response.text[:2000]
