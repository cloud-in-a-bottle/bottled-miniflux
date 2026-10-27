import re
import time
import urllib.parse

import requests
from openhost_test_harness import OpenhostStack

HTML = {"Accept": "text/html,application/xhtml+xml"}
AUTO_SUBSCRIBED_FEED = "https://github.com/cloud-in-a-bottle/cloud-in-a-bottle/releases.atom"


def _context(stack: OpenhostStack, response: requests.Response | None) -> str:
    seen = "no response" if response is None else f"{response.status_code} {response.url} {response.text[:800]}"
    return f"last response: {seen}\n\napp logs:\n{stack.app_logs()[-5000:]}"


def _owner_page(stack: OpenhostStack, path: str) -> requests.Response:
    """GET a page as the owner's browser would, retrying while the app finishes booting.

    Miniflux answers the first proxy-authenticated request by creating a session and redirecting to /unread, so a
    request only counts once it lands on the page asked for.
    """
    deadline = time.monotonic() + 90
    response = None
    while time.monotonic() < deadline:
        try:
            response = stack.owner_session.get(f"{stack.url}{path}", headers=HTML, timeout=30)
        except requests.ConnectionError:
            response = None
        if response is not None and response.status_code == 200 and urllib.parse.urlparse(response.url).path == path:
            return response
        time.sleep(2)
    raise AssertionError(f"owner GET {path} never returned 200\n{_context(stack, response)}")


def test_owner_is_logged_in_as_admin_user(stack: OpenhostStack) -> None:
    # Without the proxy-auth header Miniflux redirects to its (local-auth-disabled) login page at /.
    # The API keys page shows the signed-in user's name (the settings form hides it when local auth is disabled).
    response = _owner_page(stack, "/keys")
    username = re.search(r"Username\s*=\s*<strong>([^<]*)</strong>", response.text)
    assert username is not None, f"no signed-in user on /keys: {response.text[-3000:]}"
    assert username.group(1) == "admin", _context(stack, response)


def test_first_start_feed_is_subscribed(stack: OpenhostStack) -> None:
    response = _owner_page(stack, "/export")
    assert f'xmlUrl="{AUTO_SUBSCRIBED_FEED}"' in response.text, _context(stack, response)


def test_anonymous_access(stack: OpenhostStack) -> None:
    page = requests.get(f"{stack.url}/unread", headers=HTML, allow_redirects=False, timeout=30)
    refused = page.status_code in (401, 403, 404) or (
        page.status_code in (302, 303, 307) and "/login" in page.headers.get("Location", "")
    )
    assert refused, f"anonymous GET /unread was not refused by the router: {page.status_code} {page.headers}"

    # /js/ is public so browsers can register the service worker without an auth redirect.
    # Any Miniflux page references them (even its login page, so this doesn't depend on SSO working).
    owner_html = stack.owner_session.get(f"{stack.url}/unread", headers=HTML, timeout=30).text
    scripts = re.findall(r'"(/js/[^"]+\.js)"', owner_html)
    assert scripts, f"no /js/ scripts referenced by the owner's page: {owner_html[:2000]}"
    for script in scripts:
        response = requests.get(f"{stack.url}{script}", allow_redirects=False, timeout=30)
        assert response.status_code == 200, f"anonymous GET {script}: {response.status_code} {response.headers}"
        assert "javascript" in response.headers.get("Content-Type", ""), response.headers


def test_database_lives_in_app_data(stack: OpenhostStack) -> None:
    assert (stack.data_dir / "pgdata").is_dir(), f"no pgdata under {stack.data_dir}: {list(stack.data_dir.iterdir())}"
