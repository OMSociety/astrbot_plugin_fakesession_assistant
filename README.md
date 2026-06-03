# 合并转发伪造助手 FakesessionAssistant

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

基于 NapCat API 的合并转发消息伪造工具。支持自定义发送者、昵称、时间戳、@ 提及和图片。

> 本项目由 AI 编写，部分源码基于 [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) 。

[快速开始](#-快速开始) • [使用说明](#-使用说明) • [配置项](#-配置项说明) • [架构](#-架构)

---

## 📖 功能概览

### 合并转发伪造
一句话伪造多人聊天记录的转发消息：

- 👤 **自定义发送者** — 支持任意 QQ 号作为发送者
- 🏷️ **昵称映射** — 自动从 QQ 获取真实昵称，群聊优先取群名片；支持手动覆盖
- ⏰ **时间戳伪造** — 每条消息可指定 Unix 时间戳（可选）
- 🖼️ **图片支持** — 消息中附带图片，自动分配到对应段
- @ **提及支持** — 内容中 `@QQ号` 自动转为 @ 提及
- 📨 **群聊 & 私聊** — 自动识别会话类型，无需手写参数

---

## 🚀 快速开始

### 前置条件
- ✅ AstrBot ≥ v4
- ✅ NapCat 已运行且 HTTP API 可用（默认端口 3000）

### 第一步：配置 NapCat 连接

编辑 `config.yaml`，填入你的 NapCat HTTP API 地址：

```yaml
napcat_http_url: "http://127.0.0.1:3000"  # NapCat HTTP 地址
napcat_token: ""                            # 如启用了 token 认证则填写
```

### 第二步：安装插件

**方式一：插件市场**
- AstrBot WebUI → 插件市场 → 搜索 `SessionFaker`

**方式二：手动安装**
- 将插件文件夹放入 `/AstrBot/data/plugins/`
- 重载插件

### 依赖
核心依赖已集成在 AstrBot 环境中，无需额外安装。

---

## 📝 使用说明

### 基本语法

```
伪造消息 QQ号 内容 \| QQ号|昵称 内容 \| QQ号|昵称|时间戳 内容
```

| 符号 | 作用 |
|------|------|
| <code>&#92;&#124;</code> | 分割不同发言段 |
| <code>&#124;</code> | 段内分割 QQ号 / 昵称 / 时间戳 |

### 示例

```
伪造消息 123456 今天天气真不错

伪造消息 123456 你好 \| 654321|小王 你也好啊

伪造消息 123456|老张|1717200000 开会了 \| 789012 收到
```

### 功能细节

| 能力 | 写法 | 说明 |
|------|------|------|
| 昵称自动 | `123456 内容` | 自动从 QQ 获取（群聊优先群名片） |
| 昵称覆盖 | <code>123456&#92;&#124;老王 内容</code> | 强制使用指定昵称 |
| 时间戳 | <code>123456&#92;&#124;&#92;&#124;1717200000 内容</code> | 自定义 Unix 秒级时间戳 |
| @ 提及 | `@789012 说得对` | 在内容中 @ 其他人 |
| 图片 | `123456 看看这个[图片]` | 随消息附带图片 |

---

## ⚙️ 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `napcat_http_url` | string | `http://127.0.0.1:3000` | NapCat HTTP API 地址 |
| `napcat_token` | string | `""` | NapCat WebUI token（可选） |
| `request_timeout` | int | `10` | HTTP 请求超时（秒） |
| `nickname_cache_ttl` | int | `300` | 昵称缓存有效期（秒），0=不缓存 |
| `nickname_override` | dict | `{}` | 手动昵称映射，格式：`QQ号: 昵称` |

---

## 🏗️ 架构

```
main.py      ← 命令入口 + 事件监听 + 对话类型判断
parser.py    ← <code>&#92;&#124;</code> 切段 → 拆 QQ/昵称/时间/内容/@/图片
napcat.py    ← NapCat HTTP 客户端（get_stranger_info / get_group_member_info / send_forward_msg）
builder.py   ← parser 输出 → OneBot forward message JSON
config.yaml  ← 插件配置
```

---

## 🤝 贡献与反馈

如遇问题请在 [GitHub Issues](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues) 提交，欢迎 Pull Request！

---

## 📜 许可证

本项目采用 **MIT License** 开源协议。

---

## 👤 作者

**OMSociety** — [@OMSociety](https://github.com/OMSociety)
