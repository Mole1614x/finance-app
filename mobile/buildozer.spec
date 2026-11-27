[app]
title = ARTH
package.name = arth
package.domain = com.arth
source.dir = .
source.include_exts = py,kv,png,jpg,json,ttf
version = 0.13.0
requirements = python3==3.11.11,hostpython3==3.11.11,kivy==2.3.1,kivymd==1.2.0,pillow,numpy,opencv,pyjnius,qrcode
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,CAMERA
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, x86_64
android.ndk = 28c
android.ndk_api = 24
android.accept_sdk_license = True
android.debug_artifact = apk
p4a.branch = v2026.05.09
p4a.source_dir = .buildozer/arth-p4a-source

[buildozer]
log_level = 2
warn_on_root = 1
