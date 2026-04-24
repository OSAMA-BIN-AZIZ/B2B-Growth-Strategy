from __future__ import annotations

import json
from urllib import parse, request

from app.config import settings


class WeChatDraftService:
    def __init__(self) -> None:
        if not settings.wechat_appid or not settings.wechat_secret:
            raise RuntimeError("WECHAT_APPID/WECHAT_APPSECRET is not configured")

    def _access_token(self) -> str:
        params = parse.urlencode(
            {
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            }
        )
        url = f"https://api.weixin.qq.com/cgi-bin/token?{params}"
        with request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"failed to get access token: {data}")
        return token

    def create_draft(self, title: str, content_html: str, digest: str) -> str:
        token = self._access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        payload = {
            "articles": [
                {
                    "title": title,
                    "author": "B2B Content Growth OS",
                    "digest": digest,
                    "content": content_html,
                    "content_source_url": "",
                }
            ]
        }
        req = request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        media_id = data.get("media_id")
        if not media_id:
            raise RuntimeError(f"failed to create draft: {data}")
        return media_id
