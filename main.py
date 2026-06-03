"""合并转发伪造助手 — main.py"""
from __future__ import annotations
import os
import yaml
from pathlib import Path

from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent

from .parser import parse_message
from .napcat import NapCatClient
from .builder import build_forward_nodes

PLUGIN_DIR = Path(__file__).parent


def _load_config() -> dict:
    config_path = PLUGIN_DIR / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@register("astrbot_plugin_SessionFaker", "OMSociety", "合并转发伪造助手", "1.0.0")
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
        logger.info("[SessionFaker] 插件已初始化")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        message_text = event.message_str
        if not message_text.startswith("伪造消息"):
            return

        segments = parse_message(event)
        if not segments:
            yield event.plain_result(
                "格式：\n"
                "伪造消息 QQ号 内容 \\| QQ号|昵称 内容 \\| QQ号|昵称|时间戳 内容\n"
                "示例：伪造消息 123456 今天好冷 \\| 654321|小王 确实 \\| 789012||1717200000 记得加衣"
            )
            return

        # 确定会话类型
        group_id: str | None = None
        user_id: str | None = None
        scene_info = event.get_platform_event()
        if hasattr(scene_info, 'group_id') and scene_info.group_id:
            group_id = str(scene_info.group_id)
        elif hasattr(scene_info, 'sender_id'):
            user_id = str(scene_info.sender_id)

        # 收集昵称
        nicknames: dict[str, str] = {}
        for seg in segments:
            override = seg.nickname or self.nickname_override.get(seg.qq)
            nicknames[seg.qq] = await self.napcat.get_nickname(
                qq=seg.qq, group_id=group_id, override=override
            )
            # 也顺带查 @ 用户的昵称
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
                logger.info(f"[SessionFaker] 合并转发发送成功")
            else:
                err_msg = result.get("message") or result.get("wording") or str(result)
                logger.error(f"[SessionFaker] 发送失败: {err_msg}")
                yield event.plain_result(f"发送失败：{err_msg}")
        except Exception as e:
            logger.error(f"[SessionFaker] NapCat 请求异常: {e}")
            yield event.plain_result(f"NapCat 连接失败：{e}\n请检查 config.yaml 中 napcat_http_url 是否正确，且 NapCat 是否在运行。")

    @filter.command("伪造帮助")
    async def cmd_help(self, event: AstrMessageEvent):
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
