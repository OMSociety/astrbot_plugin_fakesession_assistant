"""
FakeSession main.py 纯函数测试

测试 OneBot 段转换、命令内容提取、组件重建等不依赖网络与实例的逻辑。
包环境由 conftest.py 模拟（main.py 使用相对导入 .parser）。
"""

from astrbot.api.message_components import Image, Plain
from fakesession_assistant.main import (
    _extract_content,
    _rebuild_components,
    _segments_to_onebot,
)

from parser import Segment


class TestSegmentsToOnebot:
    """段 → OneBot node 转换测试"""

    def test_basic_node(self):
        segs = [Segment(qq="123456", text="你好")]
        nodes = _segments_to_onebot(segs, {"123456": "小明"})
        assert len(nodes) == 1
        node = nodes[0]
        assert node["type"] == "node"
        assert node["data"]["user_id"] == 123456
        assert node["data"]["nickname"] == "小明"
        assert node["data"]["content"] == [{"type": "text", "data": {"text": "你好"}}]

    def test_nickname_fallback(self):
        segs = [Segment(qq="123456", text="你好")]
        nodes = _segments_to_onebot(segs, {})
        assert nodes[0]["data"]["nickname"] == "QQ123456"

    def test_image_node(self):
        segs = [Segment(qq="123456", text="看", images=["http://x/1.png"])]
        nodes = _segments_to_onebot(segs, {"123456": "小明"})
        content = nodes[0]["data"]["content"]
        assert {"type": "image", "data": {"file": "http://x/1.png"}} in content

    def test_empty_content_placeholder(self):
        segs = [Segment(qq="123456")]
        nodes = _segments_to_onebot(segs, {"123456": "小明"})
        assert nodes[0]["data"]["content"] == [
            {"type": "text", "data": {"text": "[图片]"}}
        ]

    def test_timestamp(self):
        segs = [Segment(qq="123456", text="hi", timestamp=1756684800)]
        nodes = _segments_to_onebot(segs, {"123456": "小明"})
        assert nodes[0]["data"]["time"] == 1756684800


class TestExtractContent:
    """命令前缀提取测试"""

    def test_extract_after_prefix(self):
        comps = [Plain("/伪造消息 123456|你好")]
        assert _extract_content(comps, "/伪造消息") == "123456|你好"

    def test_no_match_returns_empty(self):
        comps = [Plain("随便聊聊")]
        assert _extract_content(comps, "/伪造消息") == ""

    def test_prefix_only(self):
        comps = [Plain("/伪造消息")]
        assert _extract_content(comps, "/伪造消息") == ""


class TestRebuildComponents:
    """组件重建测试"""

    def test_text_replaced_images_kept(self):
        comps = [Plain("旧文本"), Image(file="http://x/1.png")]
        new = _rebuild_components(comps, "新文本")
        texts = [c.text for c in new if isinstance(c, Plain)]
        assert texts == ["新文本"]
        imgs = [c for c in new if isinstance(c, Image)]
        assert len(imgs) == 1

    def test_multiple_plain_only_first_replaced(self):
        comps = [Plain("第一段"), Plain("第二段")]
        new = _rebuild_components(comps, "新文本")
        texts = [c.text for c in new if isinstance(c, Plain)]
        assert texts == ["新文本"]
