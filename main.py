"""合并转发伪造助手 — main.py"""
from __future__ import annotations

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
        """伪造外表：/伪造外表 QQ|昵称|消息 \\| ... \\\\| 标题|摘要"""
        logger.info("[FakeSession] === 伪造外表 ===")
        try:
            content = _extract_content(event.message_obj.message, "/伪造外表")
            if not content:
                yield event.plain_result(
                    "/伪造外表 QQ|昵称|消息 \\| ... \\\\| 标题|摘要\n"
                    "示例：/伪造外表 123456|小明|你好 \\\\| 私聊|小明: 你好"
                )
                return
            parts = content.rsplit("\\|", 1)
            if len(parts) != 2:
                yield event.plain_result("格式错误，缺少 \\\\| 分割内层和外层")
                return
            inner = parts[0].rstrip("\\").strip()
            outer = parts[1].strip()
            if not inner or not outer:
                yield event.plain_result("格式错误，内层消息和外层描述都不能为空")
                return

            # 解析内层
            new_comps = _rebuild_components(event.message_obj.message, f"伪造消息{inner}")
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析内层消息。")
                return

            nicknames = {}
            for seg in segments:
                nicknames[seg.qq] = seg.nickname or await _fetch_nickname(seg.qq) or f"QQ{seg.qq}"

            # 解析外层：标题|摘要
            outer_parts = outer.split("|", 1)
            title = outer_parts[0].strip()
            summary = outer_parts[1].strip() if len(outer_parts) > 1 else f"{nicknames.get(segments[0].qq, '')}: {segments[0].text[:20] if segments else ''}"

            # 通过 OneBot WS 发送
            bot = self._get_bot(event)
            if bot is None:
                yield event.plain_result("无法连接 OneBot 适配器。")
                return
            ob_messages = _segments_to_onebot(segments, nicknames)
            msg = event.message_obj
            if getattr(msg, "group_id", None):
                await bot.call_action("send_group_forward_msg", group_id=int(msg.group_id), messages=ob_messages,
                                      news=[{"text": title, "prompt": title, "summary": summary, "source": ""}])
            else:
                await bot.call_action("send_private_forward_msg", user_id=int(msg.sender.user_id), messages=ob_messages,
                                      news=[{"text": title, "prompt": title, "summary": summary, "source": ""}])
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
            "/伪造外表 QQ|昵称|消息 \\| ... \\\\| 标题|摘要\n"
            "示例：/伪造外表 123456|小明|你好 \\\\| 私聊|小明: 你好\n\n"
            "- \\| 分割段  | 分割QQ/内容  - 图片自动分配\n"
            "- 昵称可省略，自动从API获取"
        )

    async def terminate(self):
        pass
