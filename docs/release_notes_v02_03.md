# Ver.02.03 リリースノート

## 概要

`Ver.02.03` は、`M5StampS3 + BME688` の実験運用機能を維持したまま、
GUI と firmware の内部構造を整理し、将来の拡張に備えるための
保守性向上リリースです。`v02.02` の安定判定 GUI を土台として、
責務分割、runtime hardening、recording I/O 分離、protocol capability 化を行いました。

## 含まれる主な変更

### GUI 構造整理

- `AppState` による状態保持の導入
- `dialogs.py` への dialog 分離
- `serial_worker.py`, `time_axis.py`, `qt_runtime.py` への runtime helper 分離
- `recording_io.py` への記録ファイル / partial session 補助分離
- `MainWindow` 初期化順の整理

### 時間軸 / Qt runtime の堅牢化

- `TimeAxisItem.tickStrings()` の型・空表示・例外安全性の改善
- `Clock` 表示時の安全な時刻変換
- `configure_qt_runtime()` の `QLibraryInfo` ベース解決
- Linux を含む fallback の追加

### firmware / GUI capability ハンドシェイク

- firmware に `GET_CAPS` を追加
- `protocol_version`
- `firmware_version`
- `supported_commands`
- `board_type`
- `sensor_type`
- profile 長制約と runtime profile 対応情報
- GUI 接続時に capability を取得し、ステータスへ反映

## 既存機能との関係

`Ver.02.03` では以下の既存機能を維持しています。

- Connect / Disconnect
- Record / Stop
- Start Segment / End Segment
- 名前付きヒータープロファイルプリセット
- ライブプロット
- 安定判定ランプ / 安定判定設定
- Windows `onedir` 実行ファイル

## 動作確認

- GUI 起動と基本操作の回帰なしを確認済み
- firmware ビルドと実機アップロードを確認済み
- 実機で `GET_CAPS` 応答を確認済み
- Python 構文チェックを通過

## 同梱ドキュメント

- プロジェクト概要: [README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/README.md)
- PC ロガー README: [pc_logger/README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/pc_logger/README.md)
- Windows GUI 利用ガイド: [docs/windows_gui_user_guide.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_gui_user_guide.md)
- Windows ビルド手順: [docs/windows_build.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_build.md)
- 次版バックログ: [docs/next_version_backlog.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/next_version_backlog.md)

## 次版候補

次版では、`MainWindow` 内の controller 分割、`ProfileDialog` のモデル層分離、
capability 情報の GUI 活用拡大などの整理・拡張を検討する。
