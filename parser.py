"""消息解析器 — 按 \\| 切段，每段拆 QQ/昵称/时间/内容/@/图片"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from astrbot.api.message_components import Plain, Image
from astrbot.api import logger


@dataclass
class Segment:
    qq: str
    nickname: str | None = None          # None = 自动获取
    timestamp: int | None = None         # None = 当前时间
    text: str = ""
    images: list[str] = field(default_factory=list)  # 图片 URL
    at_users: list[str] = field(default_factory=list)  # 被 @ 的 QQ 号


def _split_raw_text(raw: str) -> list[str]:
    """用 \\| 切分消息段，不误伤内容里的 \\|"""
    parts = []
    current = []
    i = 0
    while i < len(raw):
        if raw[i:i+2] == "\\|":
            parts.append("".join(current))
            current = []
            i += 2
        else:
            current.append(raw[i])
            i += 1
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _parse_segment(block: str) -> Segment | None:
    """解析一段：QQ号[|昵称][|时间戳] 内容 [图片] [...@QQ]"""
    seg = Segment(qq="")

    # 先剥离 @提及
    at_pattern = re.compile(r'@(\d{5,12})')
    seg.at_users = at_pattern.findall(block)
    block_clean = at_pattern.sub('', block).strip()

    # 尝试在头部匹配 QQ号[|昵称][|时间戳]
    head_match = re.match(r'^(\d{5,12})(?:\|([^|]+))?(?:\|(\d{10}))?\s+', block_clean)
    if not head_match:
        return None

    seg.qq = head_match.group(1)
    seg.nickname = head_match.group(2) or None
    ts_str = head_match.group(3)
    if ts_str:
        seg.timestamp = int(ts_str)

    # 剩余部分 = 文本
    rest = block_clean[head_match.end():]
    seg.text = rest.strip()
    return seg


def parse_message(event) -> list[Segment]:
    """从 AstrMessageEvent 解析出完整消息段列表"""
    raw_text = ""
    images: list[str] = []

    if hasattr(event.message_obj, 'message'):
        for comp in event.message_obj.message:
            if isinstance(comp, Plain):
                raw_text += comp.text
            elif isinstance(comp, Image) and hasattr(comp, 'url') and comp.url:
                images.append(comp.url)

    if not raw_text.startswith("伪造消息"):
        return []

    raw_text = raw_text[len("伪造消息"):].lstrip()
    blocks = _split_raw_text(raw_text)

    segments: list[Segment] = []
    img_idx = 0

    for block in blocks:
        seg = _parse_segment(block)
        if seg is None:
            logger.debug(f"[SessionFaker] 跳过无法解析的段: {block[:40]}...")
            continue

        # 如果有图片，按顺序分配到有实际内容的段
        # 简单策略：把全部图片挂到最后一个段（或第一个有内容的段）
        segments.append(seg)

    if images:
        # 图片分配到第一个段
        segments[0].images = images

    logger.debug(f"[SessionFaker] 解析到 {len(segments)} 个消息段")
    return segments
