import secrets
import unittest
from unittest.mock import patch

import httpx

from agent_auth.local import local_identity
from agent_auth.resource import AccessTokenValidator, JwksCache, create_task_api


class HttpContractTests(unittest.IsolatedAsyncioTestCase):
    issuer = "https://identity.example.test"
    audience = "https://tasks.example.test"

    @classmethod
    def setUpClass(cls):
        cls.credentials = {agent: secrets.token_urlsafe(32) for agent in ("student", "instructor")}
        cls.identity = local_identity(cls.issuer, cls.audience, cls.credentials)

    async def asyncSetUp(self):
        self.now = 0.0
        self.identity_online = True
        self.identity_http = await self.enterAsyncContext(
            httpx.AsyncClient(transport=httpx.ASGITransport(app=self.identity), base_url=self.issuer),
        )
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self.jwks_response = await self.identity_http.get(self.jwks_url)
        self.fetch = self.enterContext(patch("agent_auth.resource.httpx.get", side_effect=self.fetch_jwks))
        cache = JwksCache(self.jwks_url, clock=lambda: self.now)
        validator = AccessTokenValidator(self.issuer, self.audience, cache)
        task_app = create_task_api(validator)
        self.tasks = await self.enterAsyncContext(
            httpx.AsyncClient(transport=httpx.ASGITransport(app=task_app), base_url=self.audience),
        )

    def fetch_jwks(self, url, **kwargs):
        self.assertEqual(url, self.jwks_url)
        if not self.identity_online:
            raise httpx.ConnectError("Identity offline")
        return self.jwks_response

    async def issue(self, agent, scope, **fields):
        return await self.identity_http.post(
            "/oauth/token",
            auth=(agent, self.credentials[agent]),
            data={"grant_type": "client_credentials", "resource": self.audience, "scope": scope, **fields},
        )

    async def call_task_api(self, token):
        return await self.tasks.post(
            "/tasks", headers={"Authorization": f"Bearer {token}"}, json={"from": "student"},
        )

    async def test_metadata_points_to_configured_issuer_and_jwks_has_only_public_key(self):
        metadata = (await self.identity_http.get("/.well-known/oauth-authorization-server")).json()
        self.assertEqual(metadata["issuer"], self.issuer)
        self.assertEqual(metadata["token_endpoint"], f"{self.issuer}/oauth/token")
        self.assertEqual(metadata["jwks_uri"], self.jwks_url)

        key, = self.jwks_response.json()["keys"]
        self.assertEqual(key["alg"], "RS256")
        self.assertTrue({"kid", "n", "e"} <= key.keys())
        self.assertTrue({"d", "p", "q"}.isdisjoint(key))

    async def test_token_response_is_uncacheable_and_actor_comes_from_verified_token(self):
        response = await self.issue("instructor", "task:issue")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.json()["token_type"], "Bearer")
        result = await self.call_task_api(response.json()["access_token"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["actor"], "instructor")

    async def test_scope_is_enforced_during_token_issuance_and_at_the_task_api(self):
        denied = await self.issue("student", "task:issue")
        self.assertEqual((denied.status_code, denied.json()["error"]), (400, "invalid_scope"))
        granted = await self.issue("student", "task:read")
        result = await self.call_task_api(granted.json()["access_token"])
        self.assertEqual((result.status_code, result.json()["error"]), (403, "insufficient_scope"))

    async def test_audience_is_enforced_at_the_task_api(self):
        response = await self.issue("instructor", "task:issue", resource=f"{self.audience}/other-service")
        self.assertEqual(response.status_code, 200)
        result = await self.call_task_api(response.json()["access_token"])
        self.assertEqual((result.status_code, result.json()["error"]), (401, "invalid_token"))

    async def test_api_uses_cached_keys_during_outage_and_recovers_after_refresh(self):
        token = (await self.issue("instructor", "task:issue")).json()["access_token"]
        self.assertEqual((await self.call_task_api(token)).status_code, 200)
        self.identity_online = False
        self.now = 59
        self.assertEqual((await self.call_task_api(token)).status_code, 200)
        self.assertEqual(self.fetch.call_count, 1)

        self.now = 60
        denied = await self.call_task_api(token)
        self.assertEqual((denied.status_code, denied.json()["error"]), (503, "temporarily_unavailable"))
        self.identity_online = True
        self.now = 62
        self.assertEqual((await self.call_task_api(token)).status_code, 200)


if __name__ == "__main__":
    unittest.main()
