[app]
title = ARTH
package.name = arth
package.domain = com.arth
source.dir = .
source.include_exts = py,kv,png,jpg,json,ttf
version = 0.9.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
