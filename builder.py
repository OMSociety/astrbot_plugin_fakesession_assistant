"""组装器 — 将 parser 输出组装成 NapCat forward message JSON"""
from astrbot.api import logger


def build_forward_nodes(segments, nicknames: dict[str, str]) -> list[dict]:
    """返回 NapCat send_forward_msg 的 messages 数组"""
    nodes = []
    for seg in segments:
        nickname = nicknames.get(seg.qq, f"用户{seg.qq}")

        # 构建消息内容段
        content = []

        # @提及
        for at_qq in seg.at_users:
            at_nick = nicknames.get(at_qq, f"用户{at_qq}")
            content.append({
                "type": "at",
                "data": {"qq": at_qq, "name": at_nick}
            })

        # 文本
        if seg.text:
            content.append({
                "type": "text",
                "data": {"text": seg.text}
            })

        # 图片
        for img_url in seg.images:
            content.append({
                "type": "image",
                "data": {"file": img_url}
            })

        node = {
            "type": "node",
            "data": {
                "user_id": int(seg.qq),
                "nickname": nickname,
                "content": content,
            }
        }

        # 自定义时间戳
        if seg.timestamp:
            node["data"]["time"] = seg.timestamp

        nodes.append(node)

    logger.debug(f"[FakeSession] 构建了 {len(nodes)} 个 forward node")
    return nodes
