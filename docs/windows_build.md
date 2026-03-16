# Windows ビルドメモ

この文書は、PC ロガー GUI の Windows 実行ファイルを生成するための
現在の方針をまとめたものです。

## パッケージング方針

主経路:

- `PyInstaller` (--onefileモード)
- 単一実行ファイル生成で配布が容易

fallback:

- `pyside6-deploy`
- deploy mode はまず `standalone`

本プロジェクトは `PySide6` と `pyqtgraph` を利用しており、Windows 実機で
`PyInstaller` によるパッケージ化成功を確認済みです。現時点では
`PyInstaller` を主経路とし、`pyside6-deploy` は fallback として扱います。

## PyInstaller でのパッケージング (主経路)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --clean main.spec
```

`main.spec` はリポジトリに含めてあり、以下をすでに反映しています。

- `src` を含む `pathex`
- `PySide6` plugin ディレクトリの動的解決
- `pyqtgraph`, `serial`, `app_metadata`, `serial_protocol` などの hiddenimports
- `windowed` 実行形式

## 想定する Windows ビルド環境

- `Windows 11`
- Python `3.12`
- `pc_logger/.venv` に作成した新しい仮想環境

## パッケージング用に準備したプロジェクトファイル

- `pc_logger/main.py`
  - packaging 用 GUI エントリポイント
- `pc_logger/main.spec`
  - `PyInstaller` 用 spec
- `pc_logger/pc_logger.pyproject`
  - 将来 `pyside6-deploy` を再試行する場合の Qt project 記述

## fallback: pyside6-deploy 再試行時のメモ

必要になった場合は Windows 上で `pc_logger/` に移動して以下を実行します。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pyside6-deploy --init main.py
pyside6-deploy -f --mode standalone main.py
```

## Windows スモークテスト項目

- Python をグローバルに入れていない状態でもアプリケーションが起動する
- serial ポートが列挙される
- デバイスへ正常に接続できる
- ライブプロットが更新される
- `Record` / `Stop` が動作する
- `Start Segment` / `End Segment` が動作する
- 3-step プロファイル更新が動作する
- profile reset でデフォルトプロファイルへ戻る
- CSV 出力が正常に保存される

## 未確定事項

- onefile 出力の起動速度や安定性が運用上十分か
- `v01.00` 前にアプリアイコンを追加するか
- リリース工程で Windows のコード署名が必要か
