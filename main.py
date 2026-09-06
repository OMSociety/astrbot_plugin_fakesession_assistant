"""合并转发伪造助手 — main.py"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrbot.api import FunctionTool, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import At, Image, Node, Nodes, Plain
from astrbot.api.star import Context, Star

from .parser import Segment as Seg
from .parser import parse_message

_PLUGIN_REF = None


async def _fetch_nickname(qq: str, event=None) -> str | None:
    """获取 QQ 昵称（OneBot get_stranger_info），失败返回 None 由调用方兜底。"""
    if event and _PLUGIN_REF:
        try:
            bot = _PLUGIN_REF._get_bot(event)
            if bot:
                info = await bot.call_action(
                    "get_stranger_info", user_id=int(qq), no_cache=False
                )
                # aiocqhttp 的 call_action 返回已解包的 data dict（失败时抛 ActionFailed，
                # 不存在 {status, retcode, data} 信封——按信封判断会恒取不到昵称）
                name = (info or {}).get("nickname") or (info or {}).get("nick")
                if name:
                    return name
        except Exception as e:  # noqa: BLE001 - 查询失败不影响主流程
            logger.debug(f"[FakeSession] OneBot 查询昵称失败: {e}")
    return None


async def _resolve_nicknames(
    segments: list, event: AstrMessageEvent | None = None
) -> dict[str, str]:
    """按 QQ 去重解析昵称：显式指定 > OneBot 查询 > QQ 号兜底。"""
    nicknames: dict[str, str] = {}
    for seg in segments:
        if seg.qq not in nicknames:
            nicknames[seg.qq] = (
                seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
            )
    return nicknames


async def _build_nodes(segments: list, event: AstrMessageEvent | None = None) -> Nodes:
    """把解析出的段构建为合并转发 Nodes（命令路径的本地渲染）。"""
    nicknames = await _resolve_nicknames(segments, event)
    nodes = []
    for seg in segments:
        content: list = [Plain(seg.text)] if seg.text else []
        content.extend(At(qq=user) for user in seg.at_users)
        for img_url in seg.images:
            content.append(Image.fromURL(img_url))
        if not content:
            content = [Plain("[图片]")]
        nodes.append(Node(uin=int(seg.qq), name=nicknames[seg.qq], content=content))
    return Nodes(nodes=nodes)


def _extract_content(text: str, prefix: str) -> str:
    """提取命令前缀之后的文本内容，无匹配返回空串。

    入参用 event.message_str：唤醒前缀（默认 /）已被管线剥离，
    私聊免前缀与群聊带 / 两种写法在此统一为以命令名开头。
    """
    if not text.startswith(prefix):
        return ""
    return text[len(prefix) :].lstrip()


def _rebuild_components(raw_msg, new_text: str) -> list:
    """把第一个纯文本组件替换为新文本，其余组件（图片等）保持原位。"""
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


def _make_news(title: str) -> list[dict] | None:
    """构造合并转发外层卡片标题（news），空标题返回 None。"""
    return (
        [{"text": title, "prompt": title, "summary": "", "source": ""}]
        if title
        else None
    )


def _segments_to_onebot(segments, nicknames: dict[str, str]) -> list:
    """把段转换为 OneBot 合并转发 node 数组（适配器直发用）。"""
    result = []
    for seg in segments:
        nick = nicknames.get(seg.qq, f"QQ{seg.qq}")
        content = []
        if seg.text:
            content.append({"type": "text", "data": {"text": seg.text}})
        content.extend({"type": "at", "data": {"qq": user}} for user in seg.at_users)
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
    description: str = "创建一条合并转发消息，用于伪造聊天记录。每段必须提供 qq 和 text，**强烈建议同时提供 nickname**（否则大概率显示为 QQ 号）。可选字段：time（Unix 秒级时间戳，用于伪造消息时间）、image（图片 URL 或本地路径，如 file:// 绝对路径）。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "params": {
                    "type": "string",
                    "description": 'JSON。格式为 {"segments":[{"qq":"...","text":"...","nickname":"...","time":1756684800,"image":"url"}],"title":"..."}。每项须含 qq/text，nickname 尽量填写，title 可选，time 为可选的 Unix 秒级时间戳，image 为可选的图片 URL 或本地路径。',
                }
            },
            "required": ["params"],
        }
    )

    async def call(self, context, params: str = "") -> str:
        event = context.context.event
        # 1. 解析 LLM 传入的 JSON（容错：非法 JSON 不崩溃）
        try:
            data = json.loads(params)
        except (json.JSONDecodeError, TypeError) as e:
            return f"参数解析失败：请传入合法的 JSON（{e}）"
        # 兼容两种 LLM 传参风格：{"segments": [...]} 或直接 [...]
        if isinstance(data, dict):
            segs = data.get("segments")
            title = data.get("title", "")
        else:
            segs = data
            title = ""
        if not isinstance(segs, list) or not segs:
            return '参数缺少 segments 列表：请提供 {"segments":[{"qq":"...","text":"..."}]}'

        # 2. 构造段（逐条容错：qq 必须为 5-12 位数字，避免 int 转换崩溃）
        segments = []
        for s in segs:
            if not isinstance(s, dict):
                continue
            qq = str(s.get("qq", "")).strip()
            if not qq.isdigit() or not (5 <= len(qq) <= 12):
                continue
            segments.append(
                Seg(
                    qq=qq,
                    nickname=s.get("nickname"),
                    text=str(s.get("text", "")),
                    timestamp=s.get("time"),  # Unix 秒级时间戳
                    images=[s["image"]] if s.get("image") else [],
                )
            )
        if not segments:
            return "参数中没有有效的段（每段至少需要 5-12 位数字的 qq）"

        # 3. 用户消息中附带的图片追加到最后一个段
        for comp in event.message_obj.message:
            if isinstance(comp, Image):
                url = getattr(comp, "url", "") or getattr(comp, "file", "")
                if url:
                    segments[-1].images.append(url)

        # 4. 昵称查询（按 QQ 去重，避免对同一 QQ 重复请求）
        nicknames = await _resolve_nicknames(segments, event)

        # 5. 发送（失败返回友好提示，不崩溃）
        if _PLUGIN_REF is None:
            return "插件尚未初始化，请稍后重试。"
        try:
            await _PLUGIN_REF._send_forward(
                event, segments, nicknames, news=_make_news(title)
            )
        except Exception as e:  # noqa: BLE001 - 兜底：发送失败返回提示，不让工具崩溃
            logger.exception(f"[FakeSession] create_forward 发送失败: {e}")
            return f"发送合并转发失败：{e}"
        return f"已发送合并转发（{len(segments)} 条消息）"


class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        global _PLUGIN_REF
        _PLUGIN_REF = self
        # 工具启停由框架自带的 inactivated_llm_tools 机制负责（WebUI 可关）
        self.context.add_llm_tools(_CreateForwardTool())
        logger.info("[FakeSession] 插件已初始化")

    def _get_bot(self, event: AstrMessageEvent):
        """获取当前平台的 OneBot 客户端实例。"""
        pid = event.get_platform_id()
        inst = self.context.get_platform_inst(pid)
        if inst and hasattr(inst, "get_client"):
            return inst.get_client()
        # 兜底：按适配器类型名找任意一个 aiocqhttp 实例
        # （get_platform_inst 按实例 ID 匹配，此处需要按 meta().name 匹配）
        for candidate in self.context.platform_manager.platform_insts:
            if candidate.meta().name == "aiocqhttp" and hasattr(
                candidate, "get_client"
            ):
                return candidate.get_client()
        return None

    async def _send_forward(self, event, segments, nicknames, news=None):
        """向群聊或私聊发送合并转发消息。"""
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
        try:
            content = _extract_content(event.message_str, "伪造消息")
            if not content:
                yield event.plain_result(
                    "/伪造消息 QQ号|内容 \\| QQ号|昵称|内容\n"
                    "示例：/伪造消息 123456|你好 \\| 654321|小王|你也好"
                )
                return
            new_comps = _rebuild_components(
                event.message_obj.message, f"伪造消息{content}"
            )
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析，请检查格式。")
                return
            yield event.chain_result([await _build_nodes(segments, event)])
        except Exception as e:  # noqa: BLE001 - 兜底：命令异常不崩溃，返回提示
            logger.exception(f"[FakeSession] 伪造消息异常: {e}")
            yield event.plain_result(f"内部错误：{e}")

    @filter.command("伪造外表")
    async def fake_appearance(self, event: AstrMessageEvent):
        try:
            content = _extract_content(event.message_str, "伪造外表")
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
            new_comps = _rebuild_components(
                event.message_obj.message, f"伪造消息{inner}"
            )
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析内层消息。")
                return
            nicknames = await _resolve_nicknames(segments, event)
            await self._send_forward(
                event,
                segments,
                nicknames,
                news=_make_news(title),
            )
            event.stop_event()
        except Exception as e:  # noqa: BLE001 - 兜底：命令异常不崩溃，返回提示
            logger.exception(f"[FakeSession] 伪造外表异常: {e}")
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
