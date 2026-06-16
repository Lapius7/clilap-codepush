# clilap-codepush

[clilap.org](https://clilap.org) codepush サービスの CLI クライアント。

## インストール

```bash
pip install clilap-codepush
```

## 使い方

```bash
codepush           # インタラクティブメニュー
codepush upload file.py
codepush get <id>
codepush setup     # 管理者トークン設定
```

`cp` コマンドも同様に使えます（システムの cp と競合する場合は `codepush` を推奨）。

## 管理機能

```bash
codepush setup     # トークン設定
codepush stats     # 統計
codepush pastes    # ペースト一覧
codepush groups    # グループ一覧
codepush purge     # 不要データ削除
```
