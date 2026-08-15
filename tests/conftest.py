"""
pytest 共享配置：模拟 AstrBot 的插件包加载环境。

main.py 使用相对导入（from .parser import ...），直接 import main 会失败。
本文件在测试收集前把插件目录注册为 fakesession_assistant 包，
使 test_main_utils.py 能以包路径导入 main.py 的纯函数。
"""

import os
import sys
import types

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import parser as _parser_module

_pkg = types.ModuleType("fakesession_assistant")
_pkg.__path__ = [_PLUGIN_DIR]
sys.modules.setdefault("fakesession_assistant", _pkg)
sys.modules["fakesession_assistant.parser"] = _parser_module
