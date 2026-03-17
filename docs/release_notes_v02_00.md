# Ver.02.00 リリースノート

## 概要

`Ver.02.00` は、`Ver.01.00` を基盤に、長時間運用時の GUI 実用性、
ファームウェア入力の堅牢性、Windows 実行ファイル運用の整理を進めた
リリースです。日常的な実験運用でのストレス低減と、トラブル時の
切り分けやすさを重視しています。

## Ver.01.00 からの主な改善

### GUI / ロギング

- 描画性能を大幅に改善
  - 固定座標系 + 軸ラベル変換へ整理
  - `clipToView` / auto downsampling / 非アンチエイリアス化
  - 受信ごとの即時再描画をやめ、短周期タイマーでまとめて更新
- 時間軸表示を改善
  - `Relative`
  - `Clock`
- サイドバーとグラフ周辺の UI を整理
- `Clear Plots` を追加
  - 画面上のトレースのみを消去
  - `Record` 中は無効化
- ログビューの行数上限を追加
- 描画保持の上限を `7時間` に設定
- 有力なシリアルポートの自動選択を導入

### ファームウェア

- プロファイル入力パースを厳格化
  - 数字以外を含むトークンを reject
- 通常ポーリング中の冗長ログを削減
- 中規模リファクタ済み構成をベースに安定化を継続

### 運用と配布

- Windows 11 上での `PyInstaller` 経路を継続利用
- 旧 CLI ロガーを `pc_logger/poc/` へアーカイブ
- ルート README / PC ロガー README / Windows ビルド手順を現行実装に合わせて更新

## 現在含まれる主な機能

### ファームウェア

- Bosch `BME68x SensorAPI` を用いた `parallel mode` 計測
- 可変長 `1..10` ステップのヒータープロファイル
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
- 時間軸切替
  - `Relative`
  - `Clock`
- `Clear Plots`
- CSV 保存

### Windows 配布

- `PyInstaller` を主経路とした `bme688_logger.exe` 生成
- Windows 11 上でのスモークテスト確認

## 既知の制約

- Windows コード署名は未実施
- アプリアイコンは未設定
- 7 時間を超える長時間保持では、古い領域の粗視化は未実装
- 分析パイプライン本体は本リリース対象外

## 同梱ドキュメント

- プロジェクト概要: [README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/README.md)
- 要件定義: [docs/requirements_v1.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/requirements_v1.md)
- Windows ビルド手順: [docs/windows_build.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_build.md)
- PC ロガー README: [pc_logger/README.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/pc_logger/README.md)
- 次版バックログ: [docs/next_version_backlog.md](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/next_version_backlog.md)
