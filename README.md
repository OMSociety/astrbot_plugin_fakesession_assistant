# 合并转发伪造助手 FakesessionAssistant

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

基于 NapCat 的合并转发消息伪造工具。支持自定义发送者、昵称、时间戳、@ 提及、图片，以及自定义外层卡片标题。

> 本项目由 AI 编写，部分源码基于 [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) 。

[快速开始](#-快速开始) · [使用说明](#-使用说明) · [配置项](#-配置项说明) · [架构](#-架构)

---

## 📖 功能概览

- 👤 **自定义发送者** — 任意 QQ 号，昵称自动获取或手动覆盖
- ⏰ **时间戳伪造** — 每条消息可指定 Unix 时间戳
- 🖼️ **图片支持** — 消息附带图片，按位置分配到对应段
- @ **提及支持** — 内容中 `@QQ号` 自动转为 @ 提及
- 🏷️ **伪造外表** — 自定义合并转发外层卡片标题
- 📨 **群聊 & 私聊** — 自动识别会话类型

---

## 🚀 快速开始

### 前置条件
- ✅ AstrBot ≥ v4
- ✅ NapCat 已运行（无需额外端口，通过 AstrBot 内部适配器通信）

### 安装

**方式一：插件市场**
- AstrBot WebUI → 插件市场 → 搜索 `fakesession_assistant`

**方式二：手动安装**
- 将插件文件夹放入 `/AstrBot/data/plugins/`
- 重载插件

---

## 📝 使用说明

### 伪造消息

```
/伪造消息 QQ号|内容 \| QQ号|昵称|内容 \| QQ号|昵称|时间戳|内容
```

| 符号 | 作用 |
|------|------|
| <code>&#92;&#124;</code> | 分割不同发言段 |
| <code>&#124;</code> | 段内分割 QQ / 昵称 / 时间戳 |

**示例**

```
/伪造消息 123456|你好 \| 654321|小王|你也好
/伪造消息 123456|老王|1717200000|开会了 \| 789012 收到
/伪造消息 123456 @789012 说得对 \| 654321|小王 [图片]
```

**行为**

| 能力 | 写法 | 说明 |
|------|------|------|
| 昵称自动 | `123456 内容` | 自动从 API 获取真实昵称 |
| 昵称覆盖 | `123456\|老王 内容` | 强制使用指定昵称 |
| 时间戳 | `123456\|\|1717200000\|内容` | 自定义 Unix 秒级时间戳 |
| @ 提及 | `@789012 说得对` | 在内容中 @ 其他人 |
| 图片 | `123456 看看[图片]` | 图片按位置分配到对应段 |

### 伪造外表

```
/伪造外表 QQ|昵称|消息 \| ... \\| 标题
```

自定义外层卡片显示的标题文字。

**示例**

```
/伪造外表 123456|小明|我喜欢你 \| 654321|小红|我也喜欢你 \\| 私密对话
```

外层显示「私密对话」，里面是小明小红的聊天记录。

---

## 🏗️ 架构

```
main.py      ← 命令入口 + 事件监听
parser.py    ← 消息解析（段切分、QQ/昵称/内容提取、图片分配）
```

---

## 🤝 贡献与反馈

如遇问题请在 [GitHub Issues](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues) 提交。

---

## 📜 许可证

本项目采用 **MIT License** 开源协议。

---

## 👤 作者

**OMSociety** — [@OMSociety](https://github.com/OMSociety)
