"""NapCat HTTP API 客户端"""
from __future__ import annotations

import time

import aiohttp

from astrbot.api import logger


class NapCatClient:
    def __init__(self, http_url: str, token: str = "", timeout: int = 10):
        self.http_url = http_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl: int = 300

    def set_cache_ttl(self, ttl: int):
        self._cache_ttl = ttl

    # ── 内部 HTTP ──────────────────────────────

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _post(self, endpoint: str, body: dict) -> dict:
        url = f"{self.http_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=self._headers(),
                                     timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                return await resp.json()

    # ── 昵称 API ──────────────────────────────

    async def get_nickname(self, qq: str, group_id: str | None = None,
                           override: str | None = None) -> str:
        """获取昵称，优先级：override > 缓存 > 群名片 > 陌生人昵称"""
        if override:
            return override
        if qq in self._cache and time.time() < self._cache[qq][1]:
            return self._cache[qq][0]

        nickname = await self._get_stranger_name(qq)

        # 群聊场景尝试拿群名片
        if group_id:
            card = await self._get_group_card(group_id, qq)
            if card:
                nickname = card

        if nickname:
            self._cache[qq] = (nickname, time.time() + self._cache_ttl)
            return nickname
        return f"用户{qq}"

    async def _get_stranger_name(self, qq: str) -> str | None:
        try:
            data = await self._post("/get_stranger_info", {"user_id": int(qq), "no_cache": False})
            if data.get("status") == "ok":
                return data["data"].get("nickname") or data["data"].get("nick")
        except Exception as e:
            logger.warning(f"[FakeSession] get_stranger_info({qq}) 失败: {e}")
        return None

    async def _get_group_card(self, group_id: str, qq: str) -> str | None:
        try:
            data = await self._post("/get_group_member_info",
                                    {"group_id": int(group_id), "user_id": int(qq), "no_cache": False})
            if data.get("status") == "ok":
                card = data["data"].get("card") or data["data"].get("card_name")
                if card:
                    return card
        except Exception as e:
            logger.debug(f"[FakeSession] get_group_member_info({group_id}, {qq}) 失败: {e}")
        return None

    # ── 健康检查 ──────────────────────────────

    async def health_check(self) -> bool:
        try:
            data = await self._post("/get_login_info", {})
            return data.get("status") == "ok"
        except Exception:
            return False

    # ── 发送合并转发 ──────────────────────────

    async def send_forward(self, group_id: str | None, user_id: str | None, messages: list[dict]) -> dict:
        body: dict = {"messages": messages}
        if group_id:
            body["group_id"] = group_id
        if user_id:
            body["user_id"] = user_id
        # 外层摘要用第一个节点的昵称
        if messages:
            first = messages[0].get("data", {})
            body["prompt"] = f"{first.get('nickname', '')} 的聊天记录"
        try:
            return await self._post("/send_forward_msg", body)
        except Exception as e:
            logger.error(f"[FakeSession] send_forward_msg 请求失败: {e}")
            raise
