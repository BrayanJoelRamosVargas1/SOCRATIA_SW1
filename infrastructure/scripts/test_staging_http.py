"""Regression checks: a catch-all login page must not pass as backend health/auth."""
import io
import unittest
from unittest.mock import patch

from check_staging_http import check


class Response(io.BytesIO):
    def __init__(self, status=200, body=b'{"status":"ok"}', content_type="application/json", scheme="https"):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.url = scheme + "://staging.example.com/health"


class StagingHTTPTests(unittest.TestCase):
    def run_check(self, response, path="/health", expected=None):
        with patch("urllib.request.urlopen", return_value=response):
            return check("https://staging.example.com", path, expected or {200})

    def test_rejects_frontend_html_instead_of_backend_health(self):
        self.assertFalse(self.run_check(Response(body=b"<html>login</html>", content_type="text/html"))["ok"])

    def test_rejects_downgrade_to_http(self):
        self.assertFalse(self.run_check(Response(scheme="http"))["ok"])

    def test_rejects_public_profile(self):
        self.assertFalse(self.run_check(Response(), "/api/v1/profile", {401, 403})["ok"])

    def test_accepts_json_health(self):
        self.assertTrue(self.run_check(Response())["ok"])


if __name__ == "__main__":
    unittest.main()
