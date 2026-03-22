# Ver.02.02 リリースノート

## 概要

`Ver.02.02` は、`M5StampS3 + BME688` の実験運用において、
ガス抵抗トレースの安定待ち判断を支援するための GUI 機能追加リリースです。
`v02.01` の接続・記録・プロファイル運用基盤を引き継ぎつつ、
安定判定ランプと安定判定設定を追加しました。

## 含まれる主な変更

### 安定判定コア

- 直近 `10 分` の振れ幅と直近 `30 秒` の振れ幅比に基づく安定判定
- 各ガス抵抗チャンネルごとの `stable / unstable / unknown / unused` 判定
- `required stable channels` の概念を含むサマリー生成

### GUI

- 左カラムに `Stability` セクションを追加
- ヒーターステップごとの安定ランプ表示
- `Stability Settings` モーダルの追加
- 安定判定パラメータの保存 / 再読込
- 安定判定状態のツールチップ表示

## 既存機能との関係

`Ver.02.02` では以下の既存機能を維持しています。

- Connect / Disconnect
- Record / Stop
- Start Segment / End Segment
- 名前付きヒータープロファイルプリセット
- ライブプロット
- Windows `onedir` 実行ファイル

## 動作確認

- GUI 上で安定判定ランプと設定変更を確認済み
- 設定保存 / 再起動後の再読込を確認済み
- 既存のライブプロット、記録、セグメント操作の回帰なしを確認済み
- Windows `onedir` パッケージでスモークテスト完了

## 同梱ドキュメント

- プロジェクト概要: [README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/README.md)
- PC ロガー README: [pc_logger/README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/pc_logger/README.md)
- Windows GUI 利用ガイド: [docs/windows_gui_user_guide.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_gui_user_guide.md)
- Windows ビルド手順: [docs/windows_build.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_build.md)
- 次版バックログ: [docs/next_version_backlog.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/next_version_backlog.md)

## 次版候補

次版では、状態管理分離、`ProfileDialog` の責務整理、protocol capability 化などの
保守性向上と追加改善を検討する。
