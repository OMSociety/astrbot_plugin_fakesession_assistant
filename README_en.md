<p align="center"><strong>English</strong> · <a href="README.md">中文</a> · <a href="README_ru.md">Русский</a> · <a href="README_ja.md">日本語</a></p>

<div align="center">

<img src="https://raw.githubusercontent.com/OMSociety/astrbot_plugin_fakesession_assistant/main/logo.png" width="120" alt="FakeSession Logo" />

# FakeSession Merged-Forward Message Faker

**Generate multi-person chat-style merged-forward messages in one command** — custom senders · nicknames · timestamps · @ mentions · images · outer title

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-AGPL--3.0-orange.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/stargazers)
[![Issues](https://img.shields.io/github/issues/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues)

</div>

> This project was written by AI · The source code was developed on top of [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) · The plugin logo comes from Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153)

> **Disclaimer**: This plugin is intended for **lawful purposes only** (chat-record layout demonstrations, content creation, anti-fraud education, etc.). It is **strictly forbidden** to use it to forge chat records for fraud, defamation, impersonating others, fabricating evidence, or any other illegal or unethical conduct. The user alone bears all legal and moral responsibility arising from the use of this plugin; the author and the project assume no responsibility whatsoever.

---

## Core Features

| Feature | Description |
|------|------|
| **Custom senders** | Use any QQ number as the sender; nicknames are fetched automatically or overridden manually |
| **Image support** | Attach images to messages; they are assigned to the matching segments by position |
| **@ mention support** | `@QQ号` in the text is automatically converted into an @ mention |
| **Timestamp faking** | Set a custom send time for every message (Unix second-level timestamps) |
| **Fake outer card** | Customize the outer card title of the merged-forward message |
| **LLM tool** | The AI can directly call it to generate merged-forward messages |
| **Group & private chat** | The conversation type is detected automatically when sending |

---

## Feature Overview

### 伪造消息 (Fake Message)

The `/伪造消息` command generates a merged-forward message in the `QQ号|内容 \| QQ号|昵称|内容` format:

```
/伪造消息 123456|Hello \| 654321|XiaoWang|Nice to meet you too
```

| Symbol | Purpose |
|------|------|
| <code>&#92;&#124;</code> | Separates different message segments |
| <code>&#124;</code> | Within a segment, separates QQ / nickname / content |

**Capability cheat sheet**

| Capability | Syntax | Description |
|------|------|------|
| Auto nickname | `123456\|内容` | Fetches the real nickname from the API automatically |
| Nickname override | `123456\|老王\|内容` | Forces the specified nickname |
| @ mention | `123456\|@789012 说得对` | Mentions other people inside the text |
| Image | `123456\|看看这个`, then send an image | Images are assigned to the matching segment by position |

### 伪造外表 (Fake Outer Card)

The `/伪造外表` command customizes the outer card title of the merged-forward message:

```
/伪造外表 123456|Ming|Dinner tonight? \| 654321|Hong|Sure, see you at 7 \\| Private chat
```

The outer card shows 「Private chat」, while inside is the chat history between Ming and Hong.

---

## Quick Start

### Prerequisites

- AstrBot ≥ v4
- NapCat is running (it communicates through AstrBot's built-in aiocqhttp adapter; no extra port required)

### Step 1: Installation

AstrBot WebUI → Plugin Marketplace → search for `fakesession_assistant`

### Step 2: Usage

- Send `/伪造消息 QQ号|内容 \| QQ号|昵称|内容` in chat
- Or simply ask the AI to generate it by calling the `create_forward` tool
- English aliases: /fake-message · /fake-appearance · /fake-help

---

## LLM-Callable Tool

The plugin registers 1 LLM tool; the model decides on its own when to call it — just state what you need in natural language:

```
User: Fake a chat history between me and Ming: I say "See you tomorrow" and Ming says "Okay"
🤖 → create_forward(params={"segments":[{"qq":"123456","text":"See you tomorrow"},{"qq":"654321","nickname":"Ming","text":"Okay"}]})
    Merged-forward message sent (2 messages) ✅
```

### create_forward

Creates a merged-forward message used to fake chat records.

| Parameter | Required | Description |
|:----|:----:|:-----|
| `params` | Required | JSON string, see the format below |

**params JSON format**

```json
{
  "segments": [
    {"qq": "123456", "text": "Hello", "nickname": "Wang", "time": 1756684800, "image": "url"}
  ],
  "title": "Optional outer title"
}
```

| Field | Required | Description |
|------|:----:|------|
| `qq` | Required | QQ number (5-12 digits) |
| `text` | Required | Message text |
| `nickname` | Recommended | Nickname; if omitted, the QQ number will most likely be displayed |
| `time` | Optional | Unix second-level timestamp, used to fake the message time |
| `image` | Optional | Image URL (you may also just send an image; it is attached to the last segment automatically) |

> **Note:** Two parameter-passing styles are supported: `{"segments": [...]}`, or passing the array `[...]` directly.

---

## FAQ

### Q1: Does it require any configuration?

Commands work with essentially no configuration.

### Q2: How are nicknames obtained?

The real nickname is first looked up through the OneBot adapter; if the lookup fails, it falls back to displaying "QQ + number". You can also specify a nickname manually in the format to override it.

### Q3: Which platforms are supported?

The OneBot adapter based on NapCat (aiocqhttp); QQ group chats and private chats are supported.

### Q4: Is faking chat records legal?

This plugin is intended only for lawful demonstrations and creative work. It is **strictly forbidden** to use it for illegal purposes such as fraud, defamation, or fabricating evidence; users bear full responsibility for their own use.

## Changelog

> **[View the changelog →](CHANGELOG.md)**

## Support & Acknowledgements

If this plugin helps you, please consider giving it a Star. For questions and suggestions, feel free to open an [Issue](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues) or a [Pull Request](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/pulls).

- [AstrBot](https://github.com/AstrBotDevs/AstrBot), the open-source chatbot framework
- [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker), the upstream plugin (AGPL-3.0)
- The plugin logo comes from Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153)

## License & Author

This project is released under the **AGPL-3.0** license (inherited from the upstream SessionFaker).

[@OMSociety](https://github.com/OMSociety)
