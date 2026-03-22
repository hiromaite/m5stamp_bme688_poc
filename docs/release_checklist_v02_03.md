# Ver.02.03 リリース前チェックリスト

## 目的

`Ver.02.03` では、`v02.02` の実験運用 GUI / firmware を維持しながら、
GUI の責務分割、時間軸 / Qt runtime の堅牢化、recording I/O 分離、
firmware / GUI の capability ハンドシェイクを追加したことを確認して固定する。

## スコープ

- `pc_logger` GUI
  - `AppState` 導入
  - dialog / runtime helper / recording I/O の分離
  - `TimeAxisItem` の堅牢化
  - `configure_qt_runtime()` の強化
  - capability 取得と表示
- firmware
  - `GET_CAPS`
  - `protocol_version` / `firmware_version` / capability 応答
- 既存回帰
  - Connect / Disconnect
  - Record / Stop
  - Start Segment / End Segment
  - ライブプロット
  - 安定判定
  - Windows `onedir` packaging

## チェック項目

### 1. capability ハンドシェイク

- [x] firmware へ `GET_CAPS` を送ると `[caps]` 行が返る
- [x] `protocol_version` / `firmware_version` / `supported_commands` が返る
- [x] GUI 接続時に capability 取得が行われる
- [x] GUI ステータスへ protocol / firmware 情報が反映される

### 2. GUI 構造整理後の回帰

- [x] GUI が起動する
- [x] `ProfileDialog` / `Stability Settings` を開ける
- [x] Connect / Disconnect が動作する
- [x] Record / Stop が動作する
- [x] Start Segment / End Segment が動作する
- [x] ライブプロットが更新される
- [x] 安定判定ランプが動作する

### 3. firmware / 実機確認

- [x] firmware がビルドできる
- [x] 実機へアップロードできる
- [x] `GET_CAPS` 応答を実機で確認できる

### 4. packaging / 補助確認

- [x] Python 構文チェックが通る
- [x] Windows `onedir` packaging 方針とドキュメントが維持されている

## Ver.02.03 判定

以下を満たした時点で `Ver.02.03` として固定する。

- 上記チェック項目が完了している
- ドキュメントが現行実装と一致している
- リリースノートを作成済みである
- Git タグ `v02.03` を作成済みである
