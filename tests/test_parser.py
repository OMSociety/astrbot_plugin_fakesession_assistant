"""
FakeSession 消息解析器测试

直接测试 parser.py 的段切分、QQ/昵称/内容提取、图片分配逻辑。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from astrbot.api.message_components import Image, Plain

from parser import _parse_segment, _split_raw_text, parse_message


class TestSplitRawText:
    """段切分测试"""

    def test_basic_split(self):
        assert _split_raw_text("a\\|b") == ["a", "b"]

    def test_multi_split(self):
        assert _split_raw_text("a\\|b\\|c") == ["a", "b", "c"]

    def test_trailing_separator(self):
        assert _split_raw_text("a\\|b\\|") == ["a", "b"]

    def test_empty_blocks_dropped(self):
        assert _split_raw_text("a\\|\\|b") == ["a", "b"]

    def test_no_separator(self):
        assert _split_raw_text("只有一段") == ["只有一段"]

    def test_empty_input(self):
        assert _split_raw_text("") == []


class TestParseSegment:
    """单段解析测试"""

    def test_qq_and_text(self):
        seg = _parse_segment("123456|你好")
        assert seg.qq == "123456"
        assert seg.text == "你好"
        assert seg.nickname is None

    def test_qq_nickname_text(self):
        seg = _parse_segment("654321|小王|你也好")
        assert seg.qq == "654321"
        assert seg.nickname == "小王"
        assert seg.text == "你也好"

    def test_empty_nickname(self):
        seg = _parse_segment("123456||你好")
        assert seg.qq == "123456"
        assert seg.nickname is None
        assert seg.text == "你好"

    def test_at_users_extracted(self):
        seg = _parse_segment("123456|@789012 说得对")
        assert seg.at_users == ["789012"]
        assert seg.text == "说得对"

    def test_invalid_qq_returns_none(self):
        assert _parse_segment("abc|内容") is None
        assert _parse_segment("12|内容") is None  # 不足 5 位

    def test_qq_only(self):
        seg = _parse_segment("123456")
        assert seg.qq == "123456"
        assert seg.text == ""


class TestParseMessage:
    """整条消息解析测试"""

    def test_single_segment(self):
        comps = [Plain("伪造消息 123456|你好")]
        segs = parse_message(None, raw_components=comps)
        assert len(segs) == 1
        assert segs[0].qq == "123456"
        assert segs[0].text == "你好"

    def test_multi_segment(self):
        comps = [Plain("伪造消息 123456|你好 \\| 654321|小王|你也好")]
        segs = parse_message(None, raw_components=comps)
        assert len(segs) == 2
        assert segs[0].qq == "123456"
        assert segs[1].qq == "654321"
        assert segs[1].nickname == "小王"

    def test_without_prefix_returns_empty(self):
        comps = [Plain("123456|你好")]
        assert parse_message(None, raw_components=comps) == []

    def test_image_assigned_to_preceding_block(self):
        # 图片跟在第一段文本之后，应分配到第一段
        comps = [
            Plain("伪造消息 123456|看这个"),
            Image(file="http://example.com/1.png"),
            Plain(" \\| 654321|哈哈"),
        ]
        segs = parse_message(None, raw_components=comps)
        assert len(segs) == 2
        assert segs[0].images == ["http://example.com/1.png"]
        assert segs[1].images == []

    def test_image_after_last_block(self):
        # 图片在最后一段之后，挂到最后一段
        comps = [
            Plain("伪造消息 123456|你好 \\| 654321|哈哈"),
            Image(file="http://example.com/2.png"),
        ]
        segs = parse_message(None, raw_components=comps)
        assert len(segs) == 2
        assert segs[1].images == ["http://example.com/2.png"]

    def test_at_and_images_combined(self):
        comps = [
            Plain("伪造消息 123456|@789012 说得对 \\| 654321|小王|确实"),
            Image(file="http://example.com/3.png"),
        ]
        segs = parse_message(None, raw_components=comps)
        assert segs[0].at_users == ["789012"]
        assert segs[1].images == ["http://example.com/3.png"]

    def test_image_right_after_prefix(self):
        # 图片紧跟命令词（命令与正文之间），应分配到第一段而不是丢掉
        comps = [
            Plain("伪造消息"),
            Image(file="http://example.com/4.png"),
            Plain(" 123456|看图"),
        ]
        segs = parse_message(None, raw_components=comps)
        assert len(segs) == 1
        assert segs[0].qq == "123456"
        assert segs[0].images == ["http://example.com/4.png"]
