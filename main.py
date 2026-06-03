"""合并转发伪造助手 — main.py"""
from __future__ import annotations

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain

from .builder import build_forward_nodes
from .napcat import NapCatClient
from .parser import parse_message


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        cfg = context.get_config()
        self.napcat = NapCatClient(
            http_url=cfg.get("napcat_http_url", "http://127.0.0.1:3000"),
            token=cfg.get("napcat_token", ""),
            timeout=cfg.get("request_timeout", 10),
        )
        self.napcat.set_cache_ttl(cfg.get("nickname_cache_ttl", 300))
        logger.info("[FakeSession] 插件已初始化")

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        """伪造合并转发消息：/伪造消息 QQ号 内容 \\| QQ号|昵称 内容"""
        # 从消息链拼接完整文本（不依赖被截断的 message_str）
        chain_parts = []
        for comp in event.message_obj.message:
            if isinstance(comp, Plain):
                chain_parts.append(comp.text)
        chain_text = "".join(chain_parts)

        # 掐掉 "/伪造消息" 前缀
        prefix = "/伪造消息"
        if chain_text.startswith(prefix):
            content = chain_text[len(prefix):].lstrip()
        else:
            content = ""

        if not content:
            # DEBUG
            msg_str = event.message_str or ""
            raw_msg = event.message_obj.raw_message
            raw_str = str(raw_msg)[:200] if raw_msg else ""
            yield event.plain_result(
                f"DEBUG:\nchain_text={repr(chain_text)}\n"
                f"raw_message={repr(raw_str)}\n"
                f"message_str={repr(msg_str)}"
            )
            return

        # 重建 message_obj 以复用 parser
        fake_text = f"伪造消息{content}"
        event.message_obj.message = [Plain(fake_text)]
        event.message_obj.message_str = fake_text

        segments = parse_message(event)
        if not segments:
            yield event.plain_result(f"未能解析，原始内容: {content[:100]}")
            return

        msg = event.message_obj
        group_id: str | None = str(msg.group_id) if getattr(msg, "group_id", None) else None
        user_id: str | None = str(msg.sender.user_id) if hasattr(msg.sender, "user_id") else None

        nicknames: dict[str, str] = {}
        for seg in segments:
            nicknames[seg.qq] = await self.napcat.get_nickname(
                qq=seg.qq, group_id=group_id, override=seg.nickname
            )
            for at_qq in seg.at_users:
                if at_qq not in nicknames:
                    nicknames[at_qq] = await self.napcat.get_nickname(
                        qq=at_qq, group_id=group_id
                    )

        nodes = build_forward_nodes(segments, nicknames)
        try:
            result = await self.napcat.send_forward(group_id, user_id, nodes)
            if result.get("status") != "ok":
                err_msg = result.get("message") or result.get("wording") or str(result)
                logger.error(f"[FakeSession] 发送失败: {err_msg}")
                yield event.plain_result(f"发送失败：{err_msg}")
        except Exception as e:
            logger.error(f"[FakeSession] NapCat 请求异常: {e}")
            yield event.plain_result(f"NapCat 连接失败：{e}")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示插件帮助"""
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "【语法】\n"
            "/伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳(10位Unix) 内容\n\n"
            "【说明】\n"
            "- \\| 分割不同发言段\n"
            "- | 分割段内的 QQ/昵称/时间戳（昵称和时间戳均可省略）\n"
            "- 图片随消息附带，自动分配到对应段\n"
            "- @某人：在内容里写 @QQ号\n"
            "- 昵称默认从QQ自动获取，填写后强制覆盖\n\n"
            "【示例】\n"
            "/伪造消息 123456 今天天气真不错\n"
            "/伪造消息 123456 你好 \\| 654321|小王 你也好\n"
            "/伪造消息 123456|老张|1717200000 开会了 \\| 789012 收到"
        )

    async def terminate(self):
        pass
