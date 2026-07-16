# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "openpyxl",
        "openpyxl.cell._writer",
        "openpyxl.styles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "py",
        "_pytest",
        "pygame",
        "numpy",
        "pandas",
        "matplotlib",
        "PIL",
        "setuptools",
        "pkg_resources",
        "jaraco",
        "jaraco.text",
        "jaraco.functools",
        "jaraco.context",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HekalWorkTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HekalWorkTracker",
)

app = BUNDLE(
    coll,
    name="Hekal Work Tracker.app",
    icon=None,
    bundle_identifier="com.hekal.worktracker",
    info_plist={
        "CFBundleName": "Hekal Work Tracker",
        "CFBundleDisplayName": "Hekal Work Tracker",
        "CFBundleVersion": "1.1.1",
        "CFBundleShortVersionString": "1.1.1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
