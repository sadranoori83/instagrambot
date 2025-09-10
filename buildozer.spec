# buildozer.spec configuration file for InstaScheduler Android app

[app]
title = InstaScheduler
package.name = instascheduler
package.domain = org.yourdomain
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
version = 0.1
requirements = python3,kivy,requests,apscheduler,python-dateutil,certifi,idna,urllib3,chardet,plyer
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WAKE_LOCK,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21

# Foreground service (keeps scheduler alive in background)
# Will require extra implementation in main.py using plyer or Android Service API
# Here’s placeholder config
android.services = foreground

# (Optional) icon and presplash
icon.filename = %(source.dir)s/data/icon.png
presplash.filename = %(source.dir)s/data/presplash.png

# Logging
log_level = 2

# (Optional) screen support
android.archs = arm64-v8a,armeabi-v7a,x86,x86_64

# (Optional) if you want release build:
# android.release = True
# android.sign = True
# android.keystore = /path/to/keystore.jks
# android.keyalias = yourkeyalias
# android.keypassword = yourkeypass

# Extra Java Classes, if needed
# android.add_jars = path/to/some.jar

# Extra source dirs
# source.exclude_exts = spec,pyc,pyo

[buildozer]
log_level = 2
