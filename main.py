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
        self._context = context
        self._napcat: NapCatClient | None = None
        logger.info("[FakeSession] 插件已初始化")

    def _get_napcat(self) -> NapCatClient:
        """每次请求时重新读配置并初始化 NapCat 客户端"""
        raw = self._context.get_config()
        # WebUI 按 _conf_schema.json 分组存储为嵌套 dict，先拍平
        cfg: dict = {}
        for section in raw.values():
            if isinstance(section, dict):
                cfg.update(section)

        url = cfg.get("napcat_http_url", "http://127.0.0.1:3000")
        token = cfg.get("napcat_token", "")
        timeout = cfg.get("request_timeout", 10)
        ttl = cfg.get("nickname_cache_ttl", 300)

        if self._napcat is None or self._napcat.http_url != url:
            self._napcat = NapCatClient(http_url=url, token=token, timeout=timeout)
            self._napcat.set_cache_ttl(ttl)
            logger.info(f"[FakeSession] NapCat: {url}")
        return self._napcat

    @filter.command("伪造消息")
    async def fake_forward(self, event: AstrMessageEvent):
        """伪造合并转发：/伪造消息 QQ号 内容 \\| QQ号|昵称 内容"""
        # 从消息链拼接完整文本
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

        # 重建消息对象以复用 parser
        fake_text = f"伪造消息{content}"
        event.message_obj.message = [Plain(fake_text)]
        event.message_obj.message_str = fake_text

        segments = parse_message(event)
        if not segments:
            yield event.plain_result("未能解析，请检查格式。")
            return

        # 获取会话信息
        msg = event.message_obj
        group_id = str(msg.group_id) if getattr(msg, "group_id", None) else None
        user_id = str(msg.sender.user_id) if hasattr(msg.sender, "user_id") else None

        # 收集昵称
        napcat = self._get_napcat()
        nicknames: dict[str, str] = {}
        for seg in segments:
            nicknames[seg.qq] = await napcat.get_nickname(
                qq=seg.qq, group_id=group_id, override=seg.nickname
            )
            for at_qq in seg.at_users:
                if at_qq not in nicknames:
                    nicknames[at_qq] = await napcat.get_nickname(qq=at_qq, group_id=group_id)

        # 发送
        try:
            result = await napcat.send_forward(group_id, user_id, build_forward_nodes(segments, nicknames))
            if result.get("status") != "ok":
                err = result.get("message") or result.get("wording") or str(result)
                logger.error(f"[FakeSession] 发送失败: {err}")
                yield event.plain_result(f"发送失败：{err}")
        except Exception as e:
            logger.error(f"[FakeSession] NapCat 异常: {e}")
            yield event.plain_result(f"NapCat 连接失败：{e}")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示帮助"""
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
