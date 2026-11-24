#!/usr/bin/sh

curl -v -X POST "https://api.indexnow.org/indexnow" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "host": "stringmanolo.github.io",
    "key": "22f56c27c01591274301ed1db12646ac",
    "keyLocation": "https://stringmanolo.github.io/KyaniteAndroid/22f56c27c01591274301ed1db12646ac.txt",
    "urlList": [
      "https://stringmanolo.github.io/KyaniteAndroid/",
      "https://stringmanolo.github.io/KyaniteAndroid/ru/",
      "https://stringmanolo.github.io/KyaniteAndroid/en/",
      "https://stringmanolo.github.io/KyaniteAndroid/zh-CN/"
    ]
  }'
