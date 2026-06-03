"""合并转发伪造助手 — main.py"""
from __future__ import annotations

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain

from .parser import parse_message


async def _fetch_nickname(qq: str) -> str | None:
    """外部 API 获取 QQ 昵称"""
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
            content = [Plain("[图片]")]  # 纯图片时给条占位文本
        nodes.append(Node(uin=int(seg.qq), name=nickname, content=content))
    return Nodes(nodes=nodes)


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("[FakeSession] 插件已初始化")

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        """伪造合并转发：/伪造消息 QQ号|[昵称]|内容 \\| ..."""
        logger.info("[FakeSession] === 触发 ===")
        try:
            raw_msg = event.message_obj.message
            chain_text = "".join(
                comp.text for comp in raw_msg if isinstance(comp, Plain)
            )
            prefix = "/伪造消息"
            if not chain_text.startswith(prefix):
                yield event.plain_result("格式错误")
                return

            content = chain_text[len(prefix):].lstrip()
            if not content:
                yield event.plain_result(
                    "/伪造消息 QQ号|内容 \\| QQ号|昵称|内容\n"
                    "示例：/伪造消息 123456|你好 \\| 654321|小王|你也好"
                )
                return

            # 重建 message_obj：保留图片，只替换文本前缀
            new_text = f"伪造消息{content}"
            new_comps = []
            text_done = False
            for comp in raw_msg:
                if isinstance(comp, Plain) and not text_done:
                    new_comps.append(Plain(new_text))
                    text_done = True
                elif isinstance(comp, Plain):
                    pass  # 如果有多段 Plain，跳过（我们已合并到 new_text）
                else:
                    new_comps.append(comp)

            segments = parse_message(event, raw_components=new_comps)
            for i, seg in enumerate(segments):
                logger.info(f"[FakeSession] 段{i+1}: qq={seg.qq} text={seg.text[:30]} images={len(seg.images)}")
            if not segments:
                yield event.plain_result("未能解析，请检查格式。")
                return

            nodes = await _build_nodes(segments)
            yield event.chain_result([nodes])
        except Exception as e:
            logger.error(f"[FakeSession] 异常: {e}", exc_info=True)
            yield event.plain_result(f"内部错误：{e}")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "/伪造消息 QQ号|内容 \\| QQ号|昵称|内容\n\n"
            "- \\| 分割发言段  | 分割QQ/昵称/内容\n"
            "- 图片自动分配到对应段\n"
            "- 昵称可省略，自动从API获取\n\n"
            "示例：/伪造消息 123456|你好 \\| 654321|小王|你也好"
        )

    async def terminate(self):
        pass
