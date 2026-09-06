<div align="center">

<img src="https://raw.githubusercontent.com/OMSociety/astrbot_plugin_fakesession_assistant/main/logo.png" width="120" alt="FakeSession Logo" />

# 🎭 FakeSession 合并转发伪造助手

**一键生成多人聊天记录风格的合并转发消息** —— 自定义发送者 · 昵称 · 时间戳 · @ 提及 · 图片 · 外层标题

[![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-AGPL--3.0-orange.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/stargazers)
[![Issues](https://img.shields.io/github/issues/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues)

[✨ 核心特性](#-核心特性) • [📖 功能概览](#-功能概览) • [🚀 快速开始](#-快速开始) • [🛠️ LLM 可调用工具](#️-llm-可调用工具) • [⚠️ 常见问题](#️-常见问题) • [📝 更新日志](CHANGELOG.md)

</div>

> 🎨 本项目由 AI 编写 · 源码基于 [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) 二次开发 · 插件 Logo 来源于 Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153)

> ⚠️ **免责声明**：本插件仅用于**合法用途**（聊天记录排版演示、内容创作、反诈科普等）。**严禁**用于伪造聊天记录实施诈骗、诽谤、冒充他人、伪造证据等任何违法或不道德行为。使用本插件产生的全部法律与道德责任由使用者自行承担，作者与项目不承担任何责任。

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 👤 **自定义发送者** | 任意 QQ 号作为发送者，昵称自动获取或手动覆盖 |
| 🖼️ **图片支持** | 消息附带图片，按位置自动分配到对应发言段 |
| 📢 **@ 提及支持** | 内容中 `@QQ号` 自动转为 @ 提及 |
| ⏰ **时间戳伪造** | 自定义每条消息的发送时间（Unix 秒级时间戳） |
| 🏷️ **伪造外表** | 自定义合并转发外层卡片标题 |
| 🤖 **LLM 工具** | AI 可直接调用生成合并转发 |
| 📨 **群聊 & 私聊** | 自动识别会话类型发送 |

---

## 📖 功能概览

### 伪造消息

`/伪造消息` 命令，按 `QQ号|内容 \| QQ号|昵称|内容` 格式生成合并转发：

```
/伪造消息 123456|你好 \| 654321|小王|你也好
```

| 符号 | 作用 |
|------|------|
| <code>&#92;&#124;</code> | 分割不同发言段 |
| <code>&#124;</code> | 段内分割 QQ / 昵称 / 内容 |

**能力速查**

| 能力 | 写法 | 说明 |
|------|------|------|
| 昵称自动 | `123456\|内容` | 自动从 API 获取真实昵称 |
| 昵称覆盖 | `123456\|老王\|内容` | 强制使用指定昵称 |
| @ 提及 | `123456\|@789012 说得对` | 在内容中 @ 其他人 |
| 图片 | `123456\|看看这个` 再发图 | 图片按位置分配到对应段 |

### 伪造外表

`/伪造外表` 命令，自定义合并转发外层卡片标题：

```
/伪造外表 123456|小明|我喜欢你 \| 654321|小红|我也喜欢你 \\| 私密对话
```

外层显示「私密对话」，里面是小明和小红的聊天记录。

---

## 🚀 快速开始

### 前置条件

- ✅ AstrBot ≥ v4
- ✅ NapCat 已运行（通过 AstrBot 内部 aiocqhttp 适配器通信，无需额外端口）

### 第一步：安装

**方式一：插件市场**
- AstrBot WebUI → 插件市场 → 搜索 `fakesession_assistant`

**方式二：手动安装**
- 将插件文件夹放入 `/AstrBot/data/plugins/`
- 重载插件

### 第二步：使用

- 聊天中发送 `/伪造消息 QQ号|内容 \| QQ号|昵称|内容`
- 或直接让 AI 调用 `create_forward` 工具生成

---

## 🛠️ LLM 可调用工具

插件注册 1 个 LLM 工具，模型会自动判断何时调用，你只需用自然语言说需求：

```
用户: 帮我伪造一段我和小明的聊天记录，我说"明天见"，小明说"好的"
🤖 → create_forward(params={"segments":[{"qq":"123456","text":"明天见"},{"qq":"654321","nickname":"小明","text":"好的"}]})
    已发送合并转发（2 条消息）✅
```

### create_forward

创建一条合并转发消息，用于伪造聊天记录。

| 参数 | 必填 | 说明 |
|:----|:----:|:-----|
| `params` | ✅ | JSON 字符串，格式见下 |

**params JSON 格式**

```json
{
  "segments": [
    {"qq": "123456", "text": "你好", "nickname": "老王", "time": 1756684800, "image": "url"}
  ],
  "title": "可选的外层标题"
}
```

| 字段 | 必填 | 说明 |
|------|:----:|------|
| `qq` | ✅ | QQ 号（5-12 位数字） |
| `text` | ✅ | 消息内容 |
| `nickname` | 建议 | 昵称，不填大概率显示 QQ 号 |
| `time` | 可选 | Unix 秒级时间戳，用于伪造消息时间 |
| `image` | 可选 | 图片 URL（也可直接发图，自动挂载到最后一段） |

> 💡 支持两种传参风格：`{"segments": [...]}` 或直接传数组 `[...]`。

---

## ⚠️ 常见问题

**Q：需要配置什么吗？**
A：基本无需配置即可使用命令。

**Q：昵称是怎么获取的？**
A：优先通过 OneBot 适配器查询真实昵称，查询失败时降级为「QQ+号码」显示；也可在格式中手动指定昵称覆盖。

**Q：支持哪些平台？**
A：基于 NapCat 的 OneBot 适配器（aiocqhttp），支持 QQ 群聊与私聊。

**Q：伪造聊天记录合法吗？**
A：本插件仅用于合法演示与创作。**严禁**用于诈骗、诽谤、伪造证据等违法用途，使用者自行承担全部责任。

---

## ⭐ 支持本项目

如果这个插件对你有帮助，欢迎点亮 Star ⭐，有问题和建议请提交 [Issue](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues) 或 [Pull Request](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/pulls)。

## 🙏 致谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) 开源聊天机器人框架
- [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) 上游插件（AGPL-3.0）
- 插件 Logo 来源于 Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153)

---

## 📜 许可证

本项目采用 **AGPL-3.0** 开源协议（继承上游 SessionFaker）。

---

## 👤 作者

[@OMSociety](https://github.com/OMSociety)
