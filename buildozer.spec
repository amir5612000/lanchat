[app]
title = LAN Chat
package.name = lanchat
package.domain = com.shiraztablet.lanchat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0.0

requirements = python3,kivy==2.3.0,pyjnius,android,pillow,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE,POST_NOTIFICATIONS,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
