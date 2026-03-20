# Ver.02.01 リリースチェックリスト

このチェックリストは `Ver.02.01` リリース時点で実施・確認した内容を残すためのものです。

## Firmware

- [x] `~/.platformio/penv/bin/pio run -e m5stack-stamps3` が成功する
- [x] 実機へアップロードできる
- [x] `PING` / `GET_PROFILE` / `SET_PROFILE` / `RESET_PROFILE` が動作する
- [x] 可変長ヒータープロファイルが動作する
- [x] `[csv]` 出力が継続する
- [x] 冗長な `no new data available` ログを抑制しても通常動作に影響がない

## GUI

- [x] GUI が起動する
- [x] ポートスキャンで対象ポートを選択できる
- [x] `Connect` / `Disconnect` が動作する
- [x] ライブプロットが更新される
- [x] `Record` / `Stop` が動作する
- [x] `Start Segment` / `End Segment` が動作する
- [x] `Clear Plots` が動作する
- [x] `Record` 中の視認性向上が反映されている
- [x] Stop 確認ダイアログが動作する
- [x] 終了確認ダイアログが動作する
- [x] `Plot Span` と手動パン / ズームの整合が取れている
- [x] 下側グラフのセグメント帯表示が動作する
- [x] 名前付きプロファイルプリセットの保存 / 読込が動作する
- [x] 起動スプラッシュが表示される

## 記録と耐障害性

- [x] 記録中は `*.partial.csv` に出力される
- [x] `Stop` 後に正式な `*.csv` に確定する
- [x] 起動時に未完了セッション検出が動作する
- [x] flush タイマー導入後も CSV 保存が壊れていない

## Windows Packaging

- [x] Windows 11 上で `pyinstaller --clean main.spec` が成功する
- [x] `dist/bme688_logger/` の `onedir` 生成になる
- [x] `dist/bme688_logger/bme688_logger.exe` が起動する
- [x] Windows 実機で GUI のスモークテストに合格する

## ドキュメント

- [x] ルート README を更新した
- [x] `pc_logger/README.md` を更新した
- [x] `docs/windows_build.md` を更新した
- [x] Windows 試験ユーザー向け説明書を追加した
- [x] 次版バックログを更新した
