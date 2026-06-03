"""合并转发伪造助手 — main.py"""
from __future__ import annotations

import json

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain

from .parser import parse_message


async def _fetch_nickname(qq: str) -> str | None:
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


async def _build_nodes(segments) -> Nodes:
    nodes = []
    for seg in segments:
        nickname = seg.nickname or await _fetch_nickname(seg.qq) or f"QQ{seg.qq}"
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
        result.append({
            "type": "node",
            "data": {"user_id": int(seg.qq), "nickname": nick, "content": content},
        })
    return result


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        from astrbot.core.provider.func_tool_manager import FuncTool
        context.add_llm_tools(FuncTool(
            name="create_forward",
            description="创建一条合并转发消息，用于伪造聊天记录或展示对话。参数: JSON 字符串，包含 segments（数组，每项 qq/nickname/text）和可选的 title（有 title 则外层卡片显示该标题）。",
            parameters={
                "type": "object",
                "properties": {
                    "params": {
                        "type": "string",
                        "description": 'JSON 字符串，例如 {"segments":[{"qq":"123456","nickname":"老王","text":"你好"},{"qq":"654321","nickname":"小李","text":"你好呀"}],"title":"私聊"}。title 可选，不填则无自定义外表。'
                    }
                },
                "required": ["params"],
            },
            handler=self.create_forward,
        ))
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
        """核心：通过 OneBot WS 发送合并转发"""
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

    # ── LLM Tool ──────────────────────────────────

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
            yield event.chain_result([await _build_nodes(segments)])
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
                nicknames[seg.qq] = seg.nickname or await _fetch_nickname(seg.qq) or f"QQ{seg.qq}"

            await self._send_forward(event, segments, nicknames, news=[{"text": title, "prompt": title, "summary": "", "source": ""}])
            event.stop_event()
        except Exception as e:
            logger.error(f"[FakeSession] 伪造外表异常: {e}", exc_info=True)
            yield event.plain_result(f"内部错误：{e}")

    # ── LLM 可调用工具 ────────────────────────────

    async def create_forward(self, event: AstrMessageEvent, params: str):
        """创建合并转发消息。参数: JSON 字符串 {"segments":[{"qq":"123","nickname":"老王","text":"你好"},...],"title":"可选标题（有则为伪造外表）"}"""
        try:
            data = json.loads(params) if isinstance(params, str) else params
            segs = data["segments"]
            title = data.get("title", "")

            # 构造简易 Segment 对象
            from .parser import Segment as Seg
            segments = []
            for s in segs:
                segments.append(Seg(qq=str(s["qq"]), nickname=s.get("nickname"), text=s.get("text", "")))

            nicknames = {}
            for seg in segments:
                nicknames[seg.qq] = seg.nickname or await _fetch_nickname(seg.qq) or f"QQ{seg.qq}"

            news = [{"text": title, "prompt": title, "summary": "", "source": ""}] if title else None
            await self._send_forward(event, segments, nicknames, news=news)
            return f"已发送合并转发（{len(segments)} 条消息）"
        except Exception as e:
            logger.error(f"[FakeSession] LLM 工具异常: {e}", exc_info=True)
            return f"发送失败：{e}"

    # ── 注册 LLM 工具 ─────────────────────────────

    def __init_llm_tools__(self):
        """插件加载时自动注册 LLM 工具"""
        from astrbot.core.provider.func_tool_manager import FuncTool
        self.context.add_llm_tools([
            FuncTool(
                name="create_forward",
                description="创建一条合并转发消息，用于伪造聊天记录或展示对话。参数: JSON 字符串，包含 segments（数组，每项 qq/nickname/text）和可选的 title（有 title 则外层卡片显示该标题）。",
                parameters={
                    "type": "object",
                    "properties": {
                        "params": {
                            "type": "string",
                            "description": 'JSON 字符串，例如 {"segments":[{"qq":"123456","nickname":"老王","text":"你好"},{"qq":"654321","nickname":"小李","text":"你好呀"}],"title":"私聊"}。title 可选，不填则无自定义外表。'
                        }
                    },
                    "required": ["params"]
                },
                handler=self.create_forward,
            )
        ])

    # ── 普通命令 ───────────────────────────────────

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
