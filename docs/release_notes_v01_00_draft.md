# Ver.01.00 リリースノート案

## 概要

`Ver.01.00` は、`M5StampS3 + BME688` を用いた H2S ベンチマーク用途の
初回実用リリースです。ファームウェアによる `parallel mode` 計測、
PC ロガー GUI による可視化と記録、Windows 11 向け実行ファイル化の
基本経路を含みます。

## 含まれる主な機能

### ファームウェア

- Bosch `BME68x SensorAPI` を用いた `parallel mode` 計測
- デフォルト 10-step ヒータープロファイル
- 可変長 `1..10` ステップのヒータープロファイル切替
- シリアル制御コマンド
  - `PING`
  - `GET_PROFILE`
  - `SET_PROFILE`
  - `RESET_PROFILE`
- CSV 向けのフレーム化された出力

### PC ロガー GUI

- シリアルポートスキャン
- Connect / Disconnect
- Record / Stop
- Start Segment / End Segment
- 現在のヒータープロファイル表示
- ヒータープロファイル編集モーダル
- 温湿度・気圧・ガス抵抗・ヒーター温度のライブ表示
- 表示スパン切替
  - `10 min`
  - `30 min`
  - `1 hour`
  - `5 hours`
  - `All`
- CSV 保存

### Windows 配布

- `PyInstaller` を主経路とした `.exe` 生成
- Windows 11 上でのスモークテスト確認

## 既知の制約

- 長時間表示時の decimation は未実装
- Windows コード署名は未実施
- アプリアイコンは未設定
- 分析パイプライン本体は本リリース対象外

## 同梱ドキュメント

- プロジェクト概要: [README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/README.md)
- 要件定義: [docs/requirements_v1.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/requirements_v1.md)
- Windows ビルド手順: [docs/windows_build.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_build.md)
- PC ロガー README: [pc_logger/README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/pc_logger/README.md)

## リリース前の残作業

- リリース前チェックリストの完了
- ドキュメントの最終見直し
- Git タグ `v01.00` の作成
