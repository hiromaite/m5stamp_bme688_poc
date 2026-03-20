# Ver.02.01 リリースノート

## 概要

`Ver.02.01` は、`Ver.02.00` をベースに

- 実験中の信頼性
- GUI の運用 UX
- Windows 配布と起動体験

を強化したリリースです。

## 主な変更

### 記録と接続の信頼性向上

- Serial worker の停止性を改善
- `Disconnect` 時の応答性を向上
- 記録中は `*.partial.csv` へ保存し、`Stop` 時に正式な `*.csv` へ確定
- 起動時の未完了セッション検出を追加
- 接続中または記録中の Windows スリープ抑止を整理

### 実験運用 UX の改善

- `Record` 中の赤い点滅強調表示
- Stop 時の確認ダイアログ
- GUI 終了時の確認ダイアログ
- 手動パン / ズーム時に `Plot Span` 選択を解除
- 下側グラフ上部へのセグメント帯表示

### 長時間運用と可視化の改善

- 描画性能を改善し、長時間運用時の操作性を向上
- 7 時間保持の履歴上限を導入
- Event Log のブロック数上限を導入
- `Clear Plots` を追加

### プロファイル運用の改善

- 名前付きヒータープロファイルプリセットの保存 / 読込を追加
- GUI 再起動後もプリセットを再利用可能

### Windows 配布の改善

- Packaging 主経路を `PyInstaller onedir` へ変更
- 起動スプラッシュを追加
- Windows 11 実機で `onedir` 配布のスモークテストを完了

## 既知の制約

- 抵抗値の安定判定と通知機能は次版以降の候補です
- GUI 状態管理の本格的な分離や `ProfileDialog` のモデル層分離は今後の整理候補です
- `configure_qt_runtime()` のクロスプラットフォーム整理は今後の改善候補です

## 関連文書

- [Windows ビルドメモ](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_build.md)
- [Windows GUI アプリ利用ガイド](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/windows_gui_user_guide.md)
- [次版バックログ](/Users/hiromasa/Documents/PlatformIO/Projects/m5stamp_bme688_poc/docs/next_version_backlog.md)
