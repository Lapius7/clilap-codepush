# clilap-codepush

[codepush.clilap.org](https://codepush.clilap.org) のCLIクライアント。ファイルのアップロード・取得・管理をターミナル上のインタラクティブTUIで操作できます。

## 目次

- [インストール](#インストール)
- [使い方](#使い方)
- [機能](#機能)
- [自分のファイル管理](#自分のファイル管理)
- [有効期限のカスタム指定](#有効期限のカスタム指定)
- [管理キーについて](#管理キーについて)
- [環境変数](#環境変数)
- [動作環境](#動作環境)
- [トラブルシューティング](#トラブルシューティング)
- [ライセンス](#ライセンス)

## インストール

```bash
pip install clilap-codepush
```

更新する場合（`pip install` だけではバージョンが上がりません）:

```bash
pip install --upgrade clilap-codepush
```

> グローバル環境を汚したくない場合は [pipx](https://pipx.pypa.io/) でも導入できます: `pipx install clilap-codepush` / `pipx upgrade clilap-codepush`

## 使い方

### インタラクティブメニュー（推奨）

```bash
codepush
```

矢印キーで項目を選択し Enter で実行。Ctrl+C で終了。

### コマンドライン

```bash
codepush upload <file>   # ファイルをアップロード
codepush get <id>        # ファイルを取得（stdout 出力）
codepush myfiles         # 自分のファイル一覧
codepush diff            # 2ファイルの差分表示
codepush health          # サーバー状態確認
codepush help            # ヘルプ表示
```

## 機能

| 機能 | 説明 |
|------|------|
| アップロード | テキスト・コード・zipなど。有効期限を設定可能（無期限/1時間/1日/7日/30日/カスタム） |
| ダウンロード | IDを指定してファイルをstdoutまたはファイルに保存 |
| 自分のファイル | アップロード済みファイルの一覧・詳細・削除・上書き・サーバー上の存在確認 |
| Diff | 2つのペーストの差分をカラー表示 |
| Health | サーバーの稼働状態・DB状態・総ファイル数を確認 |
| フォルダアップロード | tar.gz / zip をまとめてアップロードし、ファイルツリーとして共有 |
| パスワード保護 | アップロード時にパスワードを設定し、取得時に要求 |

## 自分のファイル管理

`codepush myfiles`（またはメニューの「自分のファイル」）でアップロード履歴を一覧表示します。

- 一覧を開くと、各ファイルがサーバー上にまだ存在するか（削除済み・期限切れでないか）を裏で並列に確認します
- サーバー上に存在しないファイルは **ID・ファイル名が赤色** で表示され、詳細画面を開くことはできません
- `r` キーで存在確認を再実行できます
- `d` で削除、`u` で上書き（再アップロード）

これはローカルの `keys.json` （後述）に記録されているだけの情報であり、サーバー側で実際に削除・失効したものを検知して見た目で区別するための機能です。

## 有効期限のカスタム指定

```
3d12h     # 3日12時間
2h30m     # 2時間30分
90m       # 90分
7200s     # 7200秒（= 2時間）
7200      # 数字のみは秒として扱う
```

## 管理キーについて

アップロード時に発行される管理キー（`delete_key`）は `~/.config/clilap-codepush/keys.json` に自動保存されます。「自分のファイル」メニューから削除・上書きが可能です。

curlでの操作例:

```bash
# 上書き
curl clilap.org/cp/<id> -F file=@new.py -F key=<delete_key>

# 削除
curl clilap.org/cp -X DELETE -d key=<delete_key>

# 統計
curl clilap.org/cp/stats/<id>
```

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `CODEPUSH_URL` | `https://codepush.clilap.org` | APIのベースURL |

## 動作環境

- Python 3.9 以上
- Windows / macOS / Linux（WSL含む）
- クリップボードコピー: `xclip` / `xsel` / `wl-copy`（Linux）、`pbcopy`（macOS）、標準（Windows）
- 追加の依存パッケージなし（標準ライブラリのみで動作）

## トラブルシューティング

- **`pip install` 後もバージョンが古い**: `pip install` は既にインストール済みの場合バージョンを確認しないため、`pip install --upgrade clilap-codepush` を使ってください。
- **`codepush` コマンドが見つからない**: Pythonの `Scripts`（Windows）/ `bin`（macOS・Linux）ディレクトリがPATHに含まれているか確認してください。
- **`pip install --break-system-packages` が必要と言われる**: Debian/Ubuntu系などでシステムPythonへの直接インストールが制限されている場合に発生します。前述の `pipx` を使うか、`--break-system-packages` を付けて実行してください。

## ライセンス

MIT
