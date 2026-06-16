# clilap-codepush

[codepush.clilap.org](https://codepush.clilap.org) のCLIクライアント。ファイルのアップロード・取得・管理をターミナル上のインタラクティブTUIで操作できます。

## インストール

```bash
pipx install clilap-codepush
```

> `pipx` がない場合: `pip install pipx` でインストールするか、`pip install clilap-codepush --break-system-packages` でも可。

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
```

## 機能

| 機能 | 説明 |
|------|------|
| アップロード | テキスト・コード・zipなど。有効期限を設定可能（無期限/1時間/1日/7日/30日/カスタム） |
| ダウンロード | IDを指定してファイルをstdoutまたはファイルに保存 |
| 自分のファイル | アップロード済みファイルの一覧・詳細・削除・上書き |
| Diff | 2つのペーストの差分をカラー表示 |
| Health | サーバーの稼働状態・DB状態・総ファイル数を確認 |

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
curl codepush.clilap.org/cp/<id> -F file=@new.py -F key=<delete_key>

# 削除
curl codepush.clilap.org/cp -X DELETE -d key=<delete_key>

# 統計
curl codepush.clilap.org/cp/stats/<id>
```

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `CODEPUSH_URL` | `https://codepush.clilap.org` | APIのベースURL |

## 動作環境

- Python 3.9 以上
- Windows / macOS / Linux（WSL含む）
- クリップボードコピー: `xclip` / `xsel` / `wl-copy`（Linux）、`pbcopy`（macOS）、標準（Windows）

## ライセンス

MIT
