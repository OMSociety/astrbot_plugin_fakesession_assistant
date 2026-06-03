"""合并转发伪造助手 — main.py"""
from __future__ import annotations
import yaml
from pathlib import Path

from astrbot.api import logger, Context, Star
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import EventMessageType, register

from .parser import parse_message
from .napcat import NapCatClient
from .builder import build_forward_nodes

PLUGIN_DIR = Path(__file__).parent


def _load_config() -> dict:
    """加载 config.yaml，优先读 data 目录，不存在则读插件目录"""
    data_dir = Path("data/config")
    data_config = data_dir / "fakesession_config.yaml"
    if data_config.exists():
        with open(data_config, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    plugin_config = PLUGIN_DIR / "config.yaml"
    if plugin_config.exists():
        with open(plugin_config, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@register("fakesession_assistant", "Slandre & LongMarch", "合并转发伪造助手", "1.0.0")
class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        cfg = _load_config()
        self.napcat = NapCatClient(
            http_url=cfg.get("napcat_http_url", "http://127.0.0.1:3000"),
            token=cfg.get("napcat_token", ""),
            timeout=cfg.get("request_timeout", 10),
        )
        self.napcat.set_cache_ttl(cfg.get("nickname_cache_ttl", 300))
        self.nickname_override: dict[str, str] = cfg.get("nickname_override", {})
        logger.info("[FakeSession] 插件已初始化")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听消息，识别「伪造消息」指令并生成合并转发"""
        if not event.message_str.startswith("伪造消息"):
            return

        segments = parse_message(event)
        if not segments:
            yield event.plain_result(
                "格式：\n"
                "伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳 内容\n"
                "示例：伪造消息 123456 今天好冷 \\| 654321|小王 确实 \\| 789012||1717200000 记得加衣"
            )
            return

        # 从消息对象直接获取会话信息
        msg = event.message_obj
        group_id: str | None = str(msg.group_id) if getattr(msg, 'group_id', None) else None
        user_id: str | None = str(msg.sender.user_id) if hasattr(msg.sender, 'user_id') else None

        # 收集昵称
        nicknames: dict[str, str] = {}
        for seg in segments:
            override = seg.nickname or self.nickname_override.get(seg.qq)
            nicknames[seg.qq] = await self.napcat.get_nickname(
                qq=seg.qq, group_id=group_id, override=override
            )
            for at_qq in seg.at_users:
                if at_qq not in nicknames:
                    nicknames[at_qq] = await self.napcat.get_nickname(
                        qq=at_qq, group_id=group_id
                    )

        # 构建并发送
        nodes = build_forward_nodes(segments, nicknames)
        try:
            result = await self.napcat.send_forward(group_id, user_id, nodes)
            if result.get("status") == "ok":
                logger.info("[FakeSession] 合并转发发送成功")
            else:
                err_msg = result.get("message") or result.get("wording") or str(result)
                logger.error(f"[FakeSession] 发送失败: {err_msg}")
                yield event.plain_result(f"发送失败：{err_msg}")
        except Exception as e:
            logger.error(f"[FakeSession] NapCat 请求异常: {e}")
            yield event.plain_result(
                f"NapCat 连接失败：{e}\n"
                f"请检查 config.yaml 中 napcat_http_url 是否正确，且 NapCat 是否在运行。"
            )

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示插件帮助"""
        yield event.plain_result(
            "📋 合并转发伪造助手 v1.0\n\n"
            "【语法】\n"
            "伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳(10位Unix) 内容\n\n"
            "【说明】\n"
            "- \\| 分割不同发言段\n"
            "- | 分割段内的 QQ/昵称/时间戳（昵称和时间戳均可省略）\n"
            "- 图片随消息附带，自动分配到对应段\n"
            "- @某人：在内容里写 @QQ号\n"
            "- 昵称默认从QQ自动获取，填写后强制覆盖\n\n"
            "【示例】\n"
            "伪造消息 123456 今天天气真不错\n"
            "伪造消息 123456 你好 \\| 654321|小王 你也好\n"
            "伪造消息 123456|老张|1717200000 开会了 \\| 789012 收到"
        )

    async def terminate(self):
        pass
