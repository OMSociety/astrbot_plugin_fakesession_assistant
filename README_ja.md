<p align="center"><a href="README.md">中文</a> · <a href="README_en.md">English</a> · <a href="README_ru.md">Русский</a> · <strong>日本語</strong></p>

<div align="center">

<img src="https://raw.githubusercontent.com/OMSociety/astrbot_plugin_fakesession_assistant/main/logo.png" width="120" alt="FakeSession Logo" />

# 🎭 FakeSession まとめ転送フェイクアシスタント

**ワンコマンドで複数人のチャット風まとめ転送メッセージを生成** —— 送信者 · ニックネーム · タイムスタンプ · @ メンション · 画像 · 外側タイトル

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant)
[![AstrBot](https://img.shields.io/badge/AstrBot-%E2%89%A5v4-green.svg)](https://github.com/AstrBotDevs/AstrBot)
[![License](https://img.shields.io/badge/license-AGPL--3.0-orange.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/stargazers)
[![Issues](https://img.shields.io/github/issues/OMSociety/astrbot_plugin_fakesession_assistant)](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues)

</div>

> 🎨 本プロジェクトは AI によって作成されました · ソースコードは [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) を基にした二次開発です · プラグインのロゴは Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153) より

> ⚠️ **免責事項**：本プラグインは**合法的な用途のみ**（チャット履歴のレイアウトデモ、コンテンツ制作、詐欺防止の啓発など）を目的としています。チャット履歴を偽装して詐欺、誹謗中傷、なりすまし、証拠偽造など、違法または不道徳な行為を行うことに利用することは**厳禁**です。本プラグインの使用によって生じるすべての法的・道徳的責任は利用者が自ら負い、作者およびプロジェクトは一切の責任を負いません。

---

## ✨ 主な特徴

| 特徴 | 説明 |
|------|------|
| 👤 **送信者をカスタマイズ** | 任意の QQ 番号を送信者に指定でき、ニックネームは自動取得または手動上書き |
| 🖼️ **画像対応** | メッセージに画像を添付でき、位置に応じて自動的に対応する発言へ割り当て |
| 📢 **@ メンション対応** | 本文内の `@QQ号` は自動的に @ メンションへ変換 |
| ⏰ **タイムスタンプ偽装** | 各メッセージの送信時刻をカスタマイズ（Unix 秒単位のタイムスタンプ） |
| 🏷️ **外側カード偽装** | まとめ転送の外側カードのタイトルをカスタマイズ |
| 🤖 **LLM ツール** | AI が直接呼び出してまとめ転送を生成 |
| 📨 **グループ & 個人チャット** | チャット種別を自動判定して送信 |

---

## 📖 機能概要

### 伪造消息（フェイクメッセージ）

`/伪造消息` コマンドは、 `QQ号|内容 \| QQ号|昵称|内容` 形式でまとめ転送を生成します：

```
/伪造消息 123456|你好 \| 654321|小王|你也好
```

| 記号 | 役割 |
|------|------|
| <code>&#92;&#124;</code> | 異なる発言セグメントを分割 |
| <code>&#124;</code> | セグメント内で QQ / ニックネーム / 内容を分割 |

**機能早見表**

| 機能 | 書き方 | 説明 |
|------|------|------|
| ニックネーム自動 | `123456\|内容` | API から実際のニックネームを自動取得 |
| ニックネーム上書き | `123456\|老王\|内容` | 指定したニックネームを強制使用 |
| @ メンション | `123456\|@789012 说得对` | 本文内で他の人をメンション |
| 画像 | `123456\|看看这个` を送った後に画像を送信 | 画像は位置に応じて対応するセグメントへ割り当て |

### 伪造外表（フェイク外側カード）

`/伪造外表` コマンドで、まとめ転送の外側カードのタイトルをカスタマイズできます：

```
/伪造外表 123456|小明|我喜欢你 \| 654321|小红|我也喜欢你 \\| 私密对话
```

外側には「私密对话」と表示され、中身は小明（シャオミン）と小红（シャオホン）のチャット履歴です。

---

## 🚀 クイックスタート

### 前提条件

- ✅ AstrBot ≥ v4
- ✅ NapCat が起動していること（AstrBot 内蔵の aiocqhttp アダプター経由で通信し、追加ポートは不要）

### ステップ 1：インストール

**方法 1：プラグインマーケット**
- AstrBot WebUI → プラグインマーケット → `fakesession_assistant` を検索

**方法 2：手動インストール**
- プラグインフォルダーを `/AstrBot/data/plugins/` に置く
- プラグインを再読み込み

### ステップ 2：使い方

- チャットで `/伪造消息 QQ号|内容 \| QQ号|昵称|内容` を送信
- または AI に `create_forward` ツールを呼び出させて直接生成

---

## 🛠️ LLM から呼び出せるツール

プラグインは 1 個の LLM ツールを登録しており、モデルが呼び出しタイミングを自動判断します。自然言語で要望を言うだけです：

```
用户: 帮我伪造一段我和小明的聊天记录，我说"明天见"，小明说"好的"
🤖 → create_forward(params={"segments":[{"qq":"123456","text":"明天见"},{"qq":"654321","nickname":"小明","text":"好的"}]})
    已发送合并转发（2 条消息）✅
```

### create_forward

チャット履歴を偽装するためのまとめ転送メッセージを作成します。

| パラメーター | 必須 | 説明 |
|:----|:----:|:-----|
| `params` | ✅ | JSON 文字列。形式は下記のとおり |

**params の JSON 形式**

```json
{
  "segments": [
    {"qq": "123456", "text": "你好", "nickname": "老王", "time": 1756684800, "image": "url"}
  ],
  "title": "可选的外层标题"
}
```

| フィールド | 必須 | 説明 |
|------|:----:|------|
| `qq` | ✅ | QQ 番号（5-12 桁の数字） |
| `text` | ✅ | メッセージ内容 |
| `nickname` | 推奨 | ニックネーム。未指定の場合は QQ 番号が表示されることが多い |
| `time` | 任意 | Unix 秒単位のタイムスタンプ。メッセージ時刻の偽装に使用 |
| `image` | 任意 | 画像 URL（画像を直接送信してもよく、最後のセグメントに自動添付されます） |

> 💡 パラメーターの渡し方は 2 種類あります：`{"segments": [...]}` 形式と、配列 `[...]` を直接渡す方法です。

---

## ⚠️ よくある質問

### Q1：設定は必要ですか？

基本的に設定なしでコマンドを使用できます。

### Q2：ニックネームはどのように取得されますか？

まず OneBot アダプター経由で実際のニックネームを照会し、失敗した場合は「QQ+番号」形式で表示されます。形式の中でニックネームを手動指定して上書きすることもできます。

### Q3：対応プラットフォームは？

NapCat ベースの OneBot アダプター（aiocqhttp）に対応し、QQ のグループチャットと個人チャットをサポートします。

### Q4：チャット履歴の偽装は合法ですか？

本プラグインは合法的なデモと創作のみを目的としています。詐欺、誹謗中傷、証拠偽造などの違法な用途への使用は**厳禁**で、利用者が全責任を負います。

## 📝 更新履歴

> 📋 **[更新履歴を見る →](CHANGELOG.md)**

---

## ⭐ このプロジェクトを応援

このプラグインが役に立ったら、ぜひ Star ⭐ をお願いします。問題や提案は [Issue](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/issues) または [Pull Request](https://github.com/OMSociety/astrbot_plugin_fakesession_assistant/pulls) でご報告ください。

## 🙏 謝辞

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) オープンソースチャットボットフレームワーク
- [astrbot_plugin_SessionFaker](https://github.com/advent259141/astrbot_plugin_SessionFaker) 上流プラグイン（AGPL-3.0）
- プラグインのロゴは Pixiv Pid: [141357153](https://www.pixiv.net/artworks/141357153) より

---

## 📜 ライセンス

本プロジェクトは **AGPL-3.0** ライセンスの下で公開されています（上流の SessionFaker を継承）。

---

## 👤 作者

[@OMSociety](https://github.com/OMSociety)
