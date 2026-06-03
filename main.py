"""合并转发伪造助手 — main.py"""
from __future__ import annotations

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image as CompImage
from astrbot.api.message_components import Node, Nodes, Plain

from .parser import parse_message


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("[FakeSession] 插件已初始化")

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        """伪造合并转发：/伪造消息 QQ号 内容 \\| QQ号|昵称 内容"""
        chain_text = "".join(
            comp.text for comp in event.message_obj.message if isinstance(comp, Plain)
        )
        prefix = "/伪造消息"
        content = chain_text[len(prefix):].lstrip() if chain_text.startswith(prefix) else ""

        if not content:
            yield event.plain_result(
                "/伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳 内容\n"
                "示例：/伪造消息 123456 今天好冷 \\| 654321|小王 确实"
            )
            return

        fake_text = f"伪造消息{content}"
        event.message_obj.message = [Plain(fake_text)]
        event.message_obj.message_str = fake_text

        segments = parse_message(event)
        if not segments:
            yield event.plain_result("未能解析，请检查格式。")
            return

        # 用 AstrBot 原生 Node/Nodes 构建合并转发（走 WebSocket，无需 HTTP）
        nodes_list = []
        for seg in segments:
            node_content = [Plain(seg.text)]
            for img_url in seg.images:
                node_content.append(CompImage.fromURL(img_url))
            nodes_list.append(Node(
                uin=int(seg.qq),
                name=seg.nickname or f"用户{seg.qq}",
                content=node_content,
            ))

        yield event.chain_result([Nodes(nodes=nodes_list)])

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "【语法】\n"
            "/伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳 内容\n\n"
            "【说明】\n"
            "- \\| 分割不同发言段  | 分割段内QQ/昵称/时间戳\n"
            "- 图片自动分配到对应段  @某人: 写 @QQ号\n"
            "- 昵称自动从QQ获取，手动指定则覆盖\n\n"
            "【示例】\n"
            "/伪造消息 123456 今天天气不错\n"
            "/伪造消息 123456 你好 \\| 654321|小王 你也好\n"
            "/伪造消息 123456|老张|1717200000 开会了 \\| 789012 收到"
        )

    async def terminate(self):
        pass
