"""消息解析器 — 按 \\| 切段，每段拆 QQ/昵称/时间/内容/@/图片"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from astrbot.api import logger
from astrbot.api.message_components import Image, Plain


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
    at_pattern = re.compile(r"@(\d{5,12})")
    seg.at_users = at_pattern.findall(block)
    block_clean = at_pattern.sub("", block).strip()

    # 尝试在头部匹配 QQ号[|昵称][|时间戳]
    head_match = re.match(r"^(\d{5,12})(?:\|([^|]+))?(?:\|(\d{10}))?\s+", block_clean)
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
    """从 AstrMessageEvent 解析出完整消息段列表，图片按位置分配到对应段"""
    raw_text = ""
    # 收集文本和图片，并记录每个图片在 Plain 流中的插入位置
    images_at: list[tuple[int, str]] = []  # (plain_offset, url)
    text_offset = 0

    if hasattr(event.message_obj, "message"):
        for comp in event.message_obj.message:
            if isinstance(comp, Plain):
                raw_text += comp.text
                text_offset += len(comp.text)
            elif isinstance(comp, Image) and hasattr(comp, "url") and comp.url:
                images_at.append((text_offset, comp.url))

    if not raw_text.startswith("伪造消息"):
        return []

    prefix_len = len("伪造消息")
    raw_text = raw_text[prefix_len:].lstrip()

    # 图片的文本偏移量需要减去前缀长度
    images_at = [(offset - prefix_len, url) for offset, url in images_at if offset > prefix_len]

    blocks = _split_raw_text(raw_text)

    segments: list[Segment] = []
    block_start_in_raw = 0

    for block in blocks:
        # 找到这个 block 在 raw_text 中的位置（从上次结束位置开始找）
        block_start = raw_text.find(block, block_start_in_raw)
        if block_start == -1:  # 理论上不会发生，但做安全处理
            logger.debug("[FakeSession] 无法定位段位置，跳过")
            continue
        block_end = block_start + len(block)
        block_start_in_raw = block_end

        seg = _parse_segment(block)
        if seg is None:
            logger.debug(f"[FakeSession] 跳过无法解析的段: {block[:40]}...")
            continue

        # 把落在当前 block 范围内的图片分配到当前段
        for offset, url in images_at:
            if block_start <= offset < block_end:
                seg.images.append(url)

        segments.append(seg)

    logger.debug(f"[FakeSession] 解析到 {len(segments)} 个消息段")
    return segments
