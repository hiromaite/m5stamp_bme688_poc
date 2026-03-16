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

本プロジェクトは `PySide6` と `pyqtgraph` を利用しているため、PyInstallerでのパッケージ化を推奨します。

## PyInstaller でのパッケージング (主経路)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller pyinstaller-hooks-contrib
pyi-makespec --onefile --windowed main.py
# main.spec を編集: pathex, hiddenimports, datas, hookspath を設定
pyinstaller --clean main.spec
```

main.spec の hiddenimports セクション:

```python
hiddenimports=[
    'pyqtgraph',
    'pyqtgraph.Qt',
    'pyqtgraph.Qt.QtCore',
    'pyqtgraph.Qt.QtGui',
    'pyqtgraph.Qt.QtWidgets',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'app_metadata',
    'serial_protocol'
],
```

main.spec の datas セクション:

```python
datas=[('C:\\Users\\hiroma-ito.NGKNTK\\Documents\\PlatformIO\\Projects\\m5stamp_bme688_poc\\pc_logger\\.venv\\Lib\\site-packages\\PySide6\\plugins', 'PySide6/plugins')],
```

## 想定する Windows ビルド環境

- `Windows 11`
- Python `3.12`
- `pc_logger/.venv` に作成した新しい仮想環境
- Visual Studio Build Tools または MSVC ツールを含む Visual Studio
- `PATH` 上で利用可能な `dumpbin`

## パッケージング用に準備したプロジェクトファイル

- `pc_logger/main.py`
  - packaging 用 GUI エントリポイント
- `pc_logger/pc_logger.pyproject`
  - Qt project 記述
- `pc_logger/pysidedeploy.spec`
  - `pyside6-deploy` 用に生成または管理する deployment 設定

## 最初のパッケージング試行

Windows 上で `pc_logger/` に移動して実行します。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pyside6-deploy -c pysidedeploy.spec -f --mode standalone
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

- 配布物として `standalone` 出力で十分か、将来的に single-file 形式が必要か
- `v01.00` 前にアプリアイコンを追加するか
- リリース工程で Windows のコード署名が必要か
