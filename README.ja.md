<div align="center">

<p align="center"><a href="README.md">English</a> | <b>日本語</b></p>

<h1 align="center">Codepush CLI</h1>

<h3 align="center">ターミナルからファイルをアップロード・取得・管理。</h3>

<p align="center"><a href="https://codepush.clilap.org">codepush.clilap.org</a> の CLI クライアント。ファイルのアップロード・取得・管理を、ターミナル上のインタラクティブな TUI で操作できます。</p>

<p align="center">
  <a href="https://github.com/Lapius7/clilap-codepush/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Lapius7/clilap-codepush?label=release&style=flat-square&color=e8833a&logo=github"></a>
  <a href="https://www.npmjs.com/package/@lapius/clilap-codepush"><img alt="npm" src="https://img.shields.io/npm/v/@lapius/clilap-codepush?style=flat-square&color=cb3837&logo=npm"></a>
  <a href="https://pypi.org/project/clilap-codepush/"><img alt="PyPI" src="https://img.shields.io/pypi/v/clilap-codepush?style=flat-square&color=3776ab&logo=pypi&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Lapius7/clilap-codepush?style=flat-square&color=97ca00"></a>
  <a href="https://github.com/Lapius7/clilap-codepush/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/Lapius7/clilap-codepush?style=flat-square&color=e3b341&logo=github"></a>
  <a href="https://github.com/Lapius7/clilap-codepush/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Lapius7/clilap-codepush?label=last%20commit&style=flat-square&color=2f81f7"></a>
</p>

<p align="center"><a href="#インストール">インストール</a> · <a href="#使い方">使い方</a> · <a href="#機能">機能</a> · <a href="#自分のファイル管理">自分のファイル管理</a> · <a href="#環境変数">環境変数</a> · <a href="#トラブルシューティング">トラブルシューティング</a></p>

</div>

---

## インストール

pnpm を使ってください。npm と pnpm の両方に入れると同じコマンドが二重になるため、`pnpm add -g` だけを使います。

```bash
pnpm add -g @lapius/clilap-codepush
```

`codepush` コマンドが入ります。Node.js 18 以上と Python 3.9 以上が必要です。更新は `pnpm add -g @lapius/clilap-codepush@latest` で行います。

pip の場合は次のとおりです。

```bash
pip install clilap-codepush
```

更新するときは `--upgrade` を付けます。`pip install` だけでは入っているバージョンは上がりません。

```bash
pip install --upgrade clilap-codepush
```

グローバル環境を汚したくない場合は [pipx](https://pipx.pypa.io/) でも入れられます。`pipx install clilap-codepush` と `pipx upgrade clilap-codepush` を使います。

## 使い方

### インタラクティブメニュー(推奨)

```bash
codepush
```

矢印キーで項目を選び、Enter で実行します。Ctrl+C で終了します。

### コマンドライン

```bash
codepush upload <file>   # ファイルをアップロード
codepush get <id>        # ファイルを取得(stdout に出力)
codepush myfiles         # 自分のファイルを管理(別名: my)
codepush delete          # myfiles と同じ画面を開く
codepush diff            # 2つのペーストの差分表示
codepush health          # サーバー状態確認
codepush version         # バージョン表示(-v, --version)
codepush help            # ヘルプ表示
```

## 機能

| 機能 | 説明 |
| --- | --- |
| アップロード | テキスト・コード・zip など。有効期限は無期限/1時間/1日/7日/30日/カスタムから選べます。 |
| ダウンロード | ID を指定して、ファイルを stdout またはファイルに保存します。 |
| 自分のファイル | アップロード済みファイルの一覧・詳細・削除・上書き・サーバー上の存在確認ができます。 |
| Diff | 2つのペーストの差分をカラーで表示します。 |
| Health | サーバーの稼働状態・DB の状態・総ファイル数を確認します。 |
| フォルダアップロード | tar.gz や zip をまとめてアップロードし、ファイルツリーとして共有します。 |
| パスワード保護 | アップロード時にパスワードを設定し、取得時に要求します。 |

## 自分のファイル管理

`codepush myfiles`(またはメニューの「自分のファイル」)で、アップロード履歴を一覧表示します。

- 一覧を開くと、各ファイルがサーバー上にまだ存在するか(削除済みや期限切れでないか)を、裏で並列に確認します。
- サーバー上にないファイルは **ID とファイル名が赤色** で表示され、詳細画面は開けません。
- `r` キーで存在確認をやり直せます。
- `d` で削除、`u` で上書き(再アップロード)ができます。

一覧はローカルの `keys.json`(後述)に記録された内容です。存在確認は、サーバー側で削除・失効したファイルを画面上で見分けるためのものです。

## 有効期限のカスタム指定

```
3d12h     # 3日12時間
2h30m     # 2時間30分
90m       # 90分
7200s     # 7200秒(= 2時間)
7200      # 数字のみは秒として扱う
```

## 管理キー

アップロード時に発行される管理キー(`delete_key`)は、`~/.config/clilap-codepush/keys.json` に自動で保存されます。「自分のファイル」メニューから、削除や上書きができます。

curl での操作例です。

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
| --- | --- | --- |
| `CODEPUSH_URL` | `https://codepush.clilap.org` | API のベース URL |

## 必要環境

- Python 3.9 以上
- Windows / macOS / Linux(WSL を含む)
- クリップボードコピー: `xclip` / `xsel` / `wl-copy`(Linux)、`pbcopy`(macOS)、Windows は標準機能
- 追加の依存パッケージなし(標準ライブラリのみで動作)

> [!NOTE]
> フォルダアップロードとパスワード保護は旧 README から引き継いだ項目です。このクライアントのコードでは確認できず、サーバー側の機能の可能性があるため、未検証です。サーバーと通信するコマンドは、今回の書き直しでは実行していません。

## トラブルシューティング

**`pip install` 後もバージョンが古い。** `pip install` はすでに入っているパッケージのバージョンを確認しません。`pip install --upgrade clilap-codepush` を使ってください。

**`codepush` コマンドが見つからない。** Python の `Scripts`(Windows)または `bin`(macOS・Linux)ディレクトリが PATH に含まれているか確認してください。

**`--break-system-packages` が必要と言われる。** Debian や Ubuntu 系で、システム Python への直接インストールが制限されている場合に出ます。前述の `pipx` を使うか、`--break-system-packages` を付けて実行してください。

## ライセンス

MIT([LICENSE](LICENSE))
