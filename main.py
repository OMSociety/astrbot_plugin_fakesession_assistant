"""合并转发伪造助手 — main.py"""
from __future__ import annotations

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain

from .parser import parse_message


def _build_nodes(segments) -> Nodes:
    """将 Segment 列表组装为 AstrBot Nodes，不依赖外部 API"""
    nodes = []
    for seg in segments:
        content = [Plain(seg.text)] if seg.text else []
        for img_url in seg.images:
            content.append(Image.fromURL(img_url))
        nodes.append(Node(
            uin=int(seg.qq),
            name=seg.nickname or f"QQ{seg.qq}",
            content=content,
        ))
    return Nodes(nodes=nodes)


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("[FakeSession] 插件已初始化")

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        """伪造合并转发：/伪造消息 QQ号 内容 \\| QQ号|昵称 内容"""
        logger.info("[FakeSession] === 触发 ===")
        try:
            chain_text = "".join(
                comp.text for comp in event.message_obj.message if isinstance(comp, Plain)
            )
            prefix = "/伪造消息"
            content = chain_text[len(prefix):].lstrip() if chain_text.startswith(prefix) else ""

            if not content:
                yield event.plain_result(
                    "/伪造消息 QQ号 内容 \\| QQ号|昵称 内容\n"
                    "示例：/伪造消息 123456 你好 \\| 654321|小王 你也好"
                )
                return

            fake_text = f"伪造消息{content}"
            event.message_obj.message = [Plain(fake_text)]
            event.message_obj.message_str = fake_text

            segments = parse_message(event)
            if not segments:
                yield event.plain_result("未能解析，请检查格式。")
                return

            nodes = _build_nodes(segments)
            yield event.chain_result([nodes])
        except Exception as e:
            logger.error(f"[FakeSession] 异常: {e}", exc_info=True)
            yield event.plain_result(f"内部错误：{e}")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "/伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳 内容\n\n"
            "- \\| 分割发言段  | 分割QQ/昵称/时间戳\n"
            "- 图片自动分配到对应段  @某人: 写 @QQ号\n"
            "- 昵称需手动指定 (QQ号|昵称)，否则显示 QQ号\n\n"
            "示例：/伪造消息 123456|老王 你好 \\| 654321|小张 你也好"
        )

    async def terminate(self):
        pass
