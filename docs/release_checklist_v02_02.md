# Ver.02.02 リリース前チェックリスト

## 目的

`Ver.02.02` では、`v02.01` の実験運用 GUI に対して、
安定判定ランプと安定判定設定を追加し、安定待ち判断を支援できることを
確認して固定する。

## スコープ

- `pc_logger` GUI
  - 安定判定コア
  - `Stability` セクション
  - 安定ランプ表示
  - `Stability Settings` モーダル
  - 設定保存 / 再読込
- 既存回帰
  - Connect / Disconnect
  - Record / Stop
  - Start Segment / End Segment
  - ライブプロット
  - ヒータープロファイル編集 / プリセット
  - Windows `onedir` 実行ファイル

## チェック項目

### 1. 安定判定機能

- [x] `Stability` セクションが表示される
- [x] 十分な履歴がたまる前は `Waiting for enough history` が表示される
- [x] 安定状態でランプが緑に変わる
- [x] 未使用ステップは `unused` として区別される

### 2. 安定判定設定

- [x] `Stability Settings` モーダルを開ける
- [x] `Threshold (%)` を変更できる
- [x] `Recent Window (s)` を変更できる
- [x] `History Window (s)` を変更できる
- [x] `Required Stable Channels` を変更できる
- [x] 設定変更後に判定結果が更新される
- [x] GUI 再起動後も設定が保持される

### 3. 既存機能の回帰

- [x] GUI が起動する
- [x] Connect / Disconnect が動作する
- [x] ライブプロットが更新される
- [x] `Record` / `Stop` が動作する
- [x] `Start Segment` / `End Segment` が動作する
- [x] 名前付きヒータープロファイルプリセットの保存 / 読込が動作する
- [x] Windows `onedir` パッケージでスモークテストに成功する

## Ver.02.02 判定

以下を満たした時点で `Ver.02.02` として固定する。

- 上記チェック項目がすべて完了している
- ドキュメントが現行実装と一致している
- リリースノートを作成済みである
- Git タグ `v02.02` を作成済みである
