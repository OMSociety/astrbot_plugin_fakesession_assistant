"""合并转发伪造助手 — main.py"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain

from .parser import parse_message

_PLUGIN_REF = None


async def _fetch_nickname(qq: str, event=None) -> str | None:
    # 优先用 OneBot 客户端查（AstrBot 已有 WS 连接）
    if event and _PLUGIN_REF:
        try:
            bot = _PLUGIN_REF._get_bot(event)
            if bot:
                data = await bot.call_action("get_stranger_info", user_id=int(qq), no_cache=False)
                if data.get("status") == "ok" or data.get("retcode") == 0:
                    info = data.get("data", {})
                    name = info.get("nickname") or info.get("nick")
                    if name:
                        return name
        except Exception:
            pass
    # 备选：外部 API
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"http://api.mmp.cc/api/qqname?qq={qq}",
                             timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get("code") == 200:
                        name = data.get("data", {}).get("name")
                        if name and name != str(qq):
                            return name
    except Exception:
        pass
    return None


async def _build_nodes(segments: list, event: AstrMessageEvent | None = None) -> Nodes:
    nodes = []
    for seg in segments:
        nickname = seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
        content: list = [Plain(seg.text)] if seg.text else []
        for img_url in seg.images:
            content.append(Image.fromURL(img_url))
        if not content:
            content = [Plain("[图片]")]
        nodes.append(Node(uin=int(seg.qq), name=nickname, content=content))
    return Nodes(nodes=nodes)


def _extract_content(raw_msg, prefix: str) -> str:
    chain_text = "".join(comp.text for comp in raw_msg if isinstance(comp, Plain))
    if not chain_text.startswith(prefix):
        return ""
    return chain_text[len(prefix):].lstrip()


def _rebuild_components(raw_msg, new_text: str) -> list:
    new_comps = []
    text_done = False
    for comp in raw_msg:
        if isinstance(comp, Plain) and not text_done:
            new_comps.append(Plain(new_text))
            text_done = True
        elif isinstance(comp, Plain):
            pass
        else:
            new_comps.append(comp)
    return new_comps


def _segments_to_onebot(segments, nicknames: dict[str, str]) -> list:
    result = []
    for seg in segments:
        nick = nicknames.get(seg.qq, f"QQ{seg.qq}")
        content = []
        if seg.text:
            content.append({"type": "text", "data": {"text": seg.text}})
        for img_url in seg.images:
            content.append({"type": "image", "data": {"file": img_url}})
        if not content:
            content = [{"type": "text", "data": {"text": "[图片]"}}]
        node = {
            "type": "node",
            "data": {"user_id": int(seg.qq), "nickname": nick, "content": content},
        }
        if seg.timestamp:
            node["data"]["time"] = seg.timestamp
        result.append(node)
    return result


@dataclass
class _CreateForwardTool(FunctionTool):
    name: str = "create_forward"
    description: str = "创建一条合并转发消息，用于伪造聊天记录。每段必须提供 qq 和 text，**强烈建议同时提供 nickname**（否则大概率显示为 QQ 号）。"
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {"params": {"type": "string", "description": 'JSON。格式为 {"segments":[{"qq":"...","text":"...","nickname":"..."}],"title":"..."}。每项须含 qq/text，nickname 尽量填写，title 可选。'}},
        "required": ["params"],
    })

    async def call(self, context, params: str = "") -> str:
        event = context.context.event
        data = json.loads(params)
        # 兼容两种 LLM 传参风格：{"segments": [...]} 或直接 [...]
        segs = data["segments"] if isinstance(data, dict) else data
        title = data.get("title", "") if isinstance(data, dict) else ""
        from .parser import Segment as Seg
        segments = [Seg(qq=str(s["qq"]), nickname=s.get("nickname"), text=s.get("text", ""),
                         timestamp=s.get("time"),  # Unix 秒级时间戳
                         images=[s["image"]] if s.get("image") else []) for s in segs]
        # 如果用户消息中附带了图片，追加到最后一个段
        from astrbot.api.message_components import Image as CompImage
        for comp in event.message_obj.message:
            if isinstance(comp, CompImage):
                url = getattr(comp, "url", "") or getattr(comp, "file", "")
                if url and segments:
                    segments[-1].images.append(url)
        nicknames = {}
        for seg in segments:
            nicknames[seg.qq] = seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
        news = [{"text": title, "prompt": title, "summary": "", "source": ""}] if title else None
        await _PLUGIN_REF._send_forward(event, segments, nicknames, news=news)
        return f"已发送合并转发（{len(segments)} 条消息）"


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        global _PLUGIN_REF
        _PLUGIN_REF = self
        if context.get_config().get("tool", {}).get("enable_llm_tool", True):
            self.context.add_llm_tools(_CreateForwardTool())
        logger.info("[FakeSession] 插件已初始化")

    def _get_bot(self, event: AstrMessageEvent):
        pid = event.get_platform_id()
        inst = self.context.get_platform_inst(pid)
        if inst and hasattr(inst, "get_client"):
            return inst.get_client()
        inst2 = self.context.get_platform("aiocqhttp")
        if inst2 and hasattr(inst2, "get_client"):
            return inst2.get_client()
        return None

    async def _send_forward(self, event, segments, nicknames, news=None):
        bot = self._get_bot(event)
        if bot is None:
            raise RuntimeError("无法连接 OneBot 适配器")
        ob = _segments_to_onebot(segments, nicknames)
        kw = {"messages": ob}
        if news:
            kw["news"] = news
        msg = event.message_obj
        if getattr(msg, "group_id", None):
            kw["group_id"] = int(msg.group_id)
            await bot.call_action("send_group_forward_msg", **kw)
        else:
            kw["user_id"] = int(event.get_sender_id())
            await bot.call_action("send_private_forward_msg", **kw)

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        logger.info("[FakeSession] === 伪造消息 ===")
        try:
            content = _extract_content(event.message_obj.message, "/伪造消息")
            if not content:
                yield event.plain_result(
                    "/伪造消息 QQ号|内容 \\| QQ号|昵称|内容\n"
                    "示例：/伪造消息 123456|你好 \\| 654321|小王|你也好"
                )
                return
            new_comps = _rebuild_components(event.message_obj.message, f"伪造消息{content}")
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析，请检查格式。")
                return
            yield event.chain_result([await _build_nodes(segments, event)])
        except Exception as e:
            logger.error(f"[FakeSession] 异常: {e}", exc_info=True)
            yield event.plain_result(f"内部错误：{e}")

    @filter.command("伪造外表")
    async def fake_appearance(self, event: AstrMessageEvent):
        logger.info("[FakeSession] === 伪造外表 ===")
        try:
            content = _extract_content(event.message_obj.message, "/伪造外表")
            if not content:
                yield event.plain_result(
                    "/伪造外表 QQ|昵称|消息 \\| ... \\\\| 标题\n"
                    "示例：/伪造外表 123456|小明|你好 \\\\| 私密对话"
                )
                return
            parts = content.rsplit("\\|", 1)
            if len(parts) != 2:
                yield event.plain_result("格式错误，缺少 \\\\| 和标题")
                return
            inner = parts[0].rstrip("\\").strip()
            title = parts[1].strip()
            if not inner or not title:
                yield event.plain_result("内层消息和标题都不能为空")
                return
            new_comps = _rebuild_components(event.message_obj.message, f"伪造消息{inner}")
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析内层消息。")
                return
            nicknames = {}
            for seg in segments:
                nicknames[seg.qq] = seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
            await self._send_forward(event, segments, nicknames, news=[{"text": title, "prompt": title, "summary": "", "source": ""}])
            event.stop_event()
        except Exception as e:
            logger.error(f"[FakeSession] 伪造外表异常: {e}", exc_info=True)
            yield event.plain_result(f"内部错误：{e}")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "【伪造消息】\n"
            "/伪造消息 QQ号|内容 \\| QQ号|昵称|内容\n"
            "示例：/伪造消息 123456|你好 \\| 654321|小王|你也好\n\n"
            "【伪造外表】\n"
            "/伪造外表 QQ|昵称|消息 \\| ... \\\\| 标题\n"
            "示例：/伪造外表 123456|小明|你好 \\\\| 私密对话\n\n"
            "- \\| 分割段  | 分割QQ/内容  - 图片自动分配\n"
            "- 昵称可省略，自动从API获取"
        )

    async def terminate(self):
        pass
