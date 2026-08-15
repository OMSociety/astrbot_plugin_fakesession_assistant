"""合并转发伪造助手 — main.py"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrbot.api import FunctionTool, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain
from astrbot.api.star import Context, Star

from .parser import Segment as Seg
from .parser import parse_message

_PLUGIN_REF = None


async def _fetch_nickname(qq: str, event=None) -> str | None:
    """获取 QQ 昵称，优先 OneBot 客户端，失败后走外部 API 兜底。"""
    # 优先用 OneBot 客户端查（AstrBot 已有 WS 连接）
    if event and _PLUGIN_REF:
        try:
            bot = _PLUGIN_REF._get_bot(event)
            if bot:
                data = await bot.call_action(
                    "get_stranger_info", user_id=int(qq), no_cache=False
                )
                if data.get("status") == "ok" or data.get("retcode") == 0:
                    info = data.get("data", {})
                    name = info.get("nickname") or info.get("nick")
                    if name:
                        return name
        except Exception as e:  # noqa: BLE001 - 兜底：查询失败不影响主流程
            logger.debug(f"[FakeSession] OneBot 查询昵称失败: {e}")
    # 备选：外部 API
    import aiohttp

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"http://api.mmp.cc/api/qqname?qq={qq}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r,
        ):
            if r.status == 200:
                data = await r.json()
                if data.get("code") == 200:
                    name = data.get("data", {}).get("name")
                    if name and name != str(qq):
                        return name
    except Exception as e:  # noqa: BLE001 - 兜底：外部 API 不可用不影响主流程
        logger.debug(f"[FakeSession] 外部 API 查询昵称失败: {e}")
    return None


async def _build_nodes(segments: list, event: AstrMessageEvent | None = None) -> Nodes:
    """把解析出的段构建为合并转发 Nodes（命令路径的本地渲染）。"""
    nodes = []
    for seg in segments:
        nickname = seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
        content: list = [Plain(seg.text)] if seg.text else []
        for img_url in seg.images:
            content.append(Image.fromURL(img_url))
        if not content:
            content = [Plain("[图片]")]
        nodes.append(Node(uin=int(seg.qq), name=nickname, content=content))
    return Nodes(nodes=nodes)


def _extract_content(raw_msg, prefix: str) -> str:
    """提取命令前缀之后的文本内容，无匹配返回空串。"""
    chain_text = "".join(comp.text for comp in raw_msg if isinstance(comp, Plain))
    if not chain_text.startswith(prefix):
        return ""
    return chain_text[len(prefix) :].lstrip()


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


def _segments_to_onebot(segments, nicknames: dict[str, str]) -> list:
    """把段转换为 OneBot 合并转发 node 数组（适配器直发用）。"""
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
        from astrbot.api.message_components import Image as CompImage

        for comp in event.message_obj.message:
            if isinstance(comp, CompImage):
                url = getattr(comp, "url", "") or getattr(comp, "file", "")
                if url and segments:
                    segments[-1].images.append(url)

        # 4. 昵称查询（按 QQ 去重，避免对同一 QQ 重复请求）
        nicknames = {}
        for seg in segments:
            if seg.qq in nicknames:
                continue
            nicknames[seg.qq] = (
                seg.nickname or await _fetch_nickname(seg.qq, event) or f"QQ{seg.qq}"
            )

        # 5. 发送（失败返回友好提示，不崩溃）
        if _PLUGIN_REF is None:
            return "插件尚未初始化，请稍后重试。"
        try:
            news = (
                [{"text": title, "prompt": title, "summary": "", "source": ""}]
                if title
                else None
            )
            await _PLUGIN_REF._send_forward(event, segments, nicknames, news=news)
        except Exception as e:  # noqa: BLE001 - 兜底：发送失败返回提示，不让工具崩溃
            logger.exception(f"[FakeSession] create_forward 发送失败: {e}")
            return f"发送合并转发失败：{e}"
        return f"已发送合并转发（{len(segments)} 条消息）"


class SessionFakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        global _PLUGIN_REF
        _PLUGIN_REF = self
        if context.get_config().get("tool", {}).get("enable_llm_tool", True):
            self.context.add_llm_tools(_CreateForwardTool())
        logger.info("[FakeSession] 插件已初始化")

    def _get_bot(self, event: AstrMessageEvent):
        """获取当前平台的 OneBot 客户端实例。"""
        pid = event.get_platform_id()
        inst = self.context.get_platform_inst(pid)
        if inst and hasattr(inst, "get_client"):
            return inst.get_client()
        inst2 = self.context.get_platform("aiocqhttp")
        if inst2 and hasattr(inst2, "get_client"):
            return inst2.get_client()
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
        logger.info("[FakeSession] === 伪造消息 ===")
        try:
            content = _extract_content(event.message_obj.message, "/伪造消息")
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
            new_comps = _rebuild_components(
                event.message_obj.message, f"伪造消息{inner}"
            )
            segments = parse_message(event, raw_components=new_comps)
            if not segments:
                yield event.plain_result("未能解析内层消息。")
                return
            nicknames = {}
            for seg in segments:
                nicknames[seg.qq] = (
                    seg.nickname
                    or await _fetch_nickname(seg.qq, event)
                    or f"QQ{seg.qq}"
                )
            await self._send_forward(
                event,
                segments,
                nicknames,
                news=[{"text": title, "prompt": title, "summary": "", "source": ""}],
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
