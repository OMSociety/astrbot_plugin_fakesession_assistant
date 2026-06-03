"""消息解析器 — QQ号|昵称|内容 格式，\\| 切段"""
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
    """用 \\| 切分消息段"""
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
    """解析 QQ号|内容 或 QQ号|昵称|内容 或 QQ号||时间戳|内容"""
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
        # QQ|内容
        seg.text = parts[1].strip()
        return seg

    # len >= 3: QQ|昵称|内容 或 QQ||时间戳|内容
    second = parts[1].strip()
    if second == "":
        # QQ||时间戳|内容
        if re.match(r"^\d{10}$", parts[2].strip()):
            seg.timestamp = int(parts[2].strip())
            seg.text = "|".join(parts[3:]).strip() if len(parts) > 3 else ""
        else:
            seg.text = "|".join(parts[2:]).strip()
    elif re.match(r"^\d{10}$", second):
        # QQ|时间戳|内容
        seg.timestamp = int(second)
        seg.text = "|".join(parts[2:]).strip()
    else:
        # QQ|昵称|内容
        seg.nickname = second
        seg.text = "|".join(parts[2:]).strip()

    return seg


def parse_message(event, raw_components: list | None = None) -> list[Segment]:
    """从 event 或原始组件列表解析消息段"""
    raw_text = ""
    images: list[str] = []
    comps = raw_components or (event.message_obj.message if hasattr(event.message_obj, "message") else [])

    for comp in comps:
        if isinstance(comp, Plain):
            raw_text += comp.text
        elif isinstance(comp, Image):
            url = getattr(comp, "url", "") or getattr(comp, "file", "")
            if url:
                images.append(url)

    if not raw_text.startswith("伪造消息"):
        return []

    raw_text = raw_text[len("伪造消息"):].lstrip()
    blocks = _split_raw_text(raw_text)
    segments: list[Segment] = []

    # 简单分配：图片按顺序给段，段不够就全给第一段
    img_idx = 0
    for block in blocks:
        seg = _parse_segment(block)
        if seg is None:
            continue
        if img_idx < len(images):
            seg.images.append(images[img_idx])
            img_idx += 1
        segments.append(seg)

    # 多余的图片挂在最后一段
    while img_idx < len(images) and segments:
        segments[-1].images.append(images[img_idx])
        img_idx += 1

    logger.debug(f"[FakeSession] 解析: {len(blocks)} 段, {len(images)} 张图片, {len(segments)} 个有效段")
    return segments
