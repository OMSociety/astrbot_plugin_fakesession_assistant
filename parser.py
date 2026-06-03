"""消息解析器 — QQ号|昵称|内容 格式，\\| 切段，按位置分配图片"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from astrbot.api import logger
from astrbot.api.message_components import Image, Plain


@dataclass
class Segment:
    qq: str
    nickname: str | None = None
    timestamp: int | None = None
    text: str = ""
    images: list[str] = field(default_factory=list)
    at_users: list[str] = field(default_factory=list)


def _split_raw_text(raw: str) -> list[str]:
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
    at_pattern = re.compile(r"@(\d{5,12})")
    at_users = at_pattern.findall(block)
    block_clean = at_pattern.sub("", block).strip()
    parts = block_clean.split("|")
    if not parts or not re.match(r"^\d{5,12}$", parts[0].strip()):
        return None

    seg = Segment(qq=parts[0].strip(), at_users=at_users)
    if len(parts) == 1:
        return seg
    if len(parts) == 2:
        seg.text = parts[1].strip()
        return seg

    second = parts[1].strip()
    if second == "":
        if re.match(r"^\d{10}$", parts[2].strip()):
            seg.timestamp = int(parts[2].strip())
            seg.text = "|".join(parts[3:]).strip() if len(parts) > 3 else ""
        else:
            seg.text = "|".join(parts[2:]).strip()
    elif re.match(r"^\d{10}$", second):
        seg.timestamp = int(second)
        seg.text = "|".join(parts[2:]).strip()
    else:
        seg.nickname = second
        seg.text = "|".join(parts[2:]).strip()

    return seg


def parse_message(event, raw_components: list | None = None) -> list[Segment]:
    """从原始组件列表解析：按 \\| 切 blocks，图片跟在其前面的 block 后"""
    comps = raw_components or (event.message_obj.message if hasattr(event.message_obj, "message") else [])

    # 第一步：收集所有 Plain 文本和图片，并记录图片之前的累计文本长度
    raw_text = ""
    image_offsets: list[tuple[int, str]] = []  # (在 raw_text 中的位置, url)
    for comp in comps:
        if isinstance(comp, Plain):
            raw_text += comp.text
        elif isinstance(comp, Image):
            url = getattr(comp, "url", "") or getattr(comp, "file", "")
            if url:
                image_offsets.append((len(raw_text), url))

    if not raw_text.startswith("伪造消息"):
        return []

    prefix_len = len("伪造消息")
    raw_text = raw_text[prefix_len:].lstrip()
    # 图片位置也要减去前缀长度
    image_offsets = [(o - prefix_len, u) for o, u in image_offsets if o > prefix_len]

    blocks = _split_raw_text(raw_text)
    segments: list[Segment] = []

    # 按 block 在 raw_text 中的位置分配图片
    pos = 0
    for block in blocks:
        block_start = raw_text.find(block, pos)
        if block_start == -1:
            pos += len(block)
            continue
        block_end = block_start + len(block)
        pos = block_end

        seg = _parse_segment(block)
        if seg is None:
            continue

        # 收集该 block 范围内的图片
        for offset, url in image_offsets:
            if block_start <= offset < block_end:
                seg.images.append(url)

        # 有文本或有图才保留
        if seg.text or seg.images:
            segments.append(seg)
        else:
            # 空段也保留，等下 assign 剩余图片
            segments.append(seg)

    # 未分配的图片（在最后一段之后）挂到最后一段
    if image_offsets and pos <= len(raw_text):
        remaining = [url for offset, url in image_offsets if offset >= pos]
        if remaining and segments:
            segments[-1].images.extend(remaining)

    logger.debug(f"[FakeSession] 解析: {len(blocks)} 段, {len(image_offsets)} 张图片, {len(segments)} 个有效段")
    return segments
