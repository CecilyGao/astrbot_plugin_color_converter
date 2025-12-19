# astrbot_plugin_color_converter
颜色转换器，支持RGB/CMYK/16进制颜色互转、图片按坐标取色等功能

# 🔧 安装
方法一：使用插件市场 (推荐)

搜索 color_converter 并安装

方法二：Git Clone

进入 AstrBot 的 data/plugins/ 目录，然后执行：

```bash
git clone https://github.com/CecilyGao/astrbot_plugin_color_converter
```

##安装依赖

本插件需要：
- aiohttp
- pillow

手动安装依赖：pip install aiohttp; pip install pillow
requirements.txt还没弄，等我有时间搞一下

~~无论使用哪种方法，插件的依赖都会在机器人下次重启时自动安装。~~

# 🚀 使用说明
## 指令1：颜色格式转换
`/color '目标格式' '颜色值'`

### 参数
- '目标格式': 想要转换成的格式，可选值: rgb, hex, cmyk
- '颜色值': 想转换的颜色值，支持以下格式:
-- 16进制: 3位或6位16进制数。示例: F00或 FF0000
-- RGB: 3个0-255的数字，用逗号分隔。示例: 255,0,0
-- CMYK: 4个0-100的数字，用逗号分隔。示例: 0,100,100,0
            
### 示例
- `/color rgb 72C0FF` - 将16进制的#72C0FF转换为RGB格式
- `/color cmyk 114,166,255` - 将RGB的(114,166,255)转换为CMYK格式
- `/color hex 55,35,0,0` - 将CMYK的（55%,35%,0%,0%）转换成16进制格式

---
## 指令2：图片坐标取色器
`/color pick '坐标' （需要引用一张图片）`

### 参数
- `坐标`: x,y 例如: 1490,532

### 示例
- `/color pick 1490,532（引用一张图片）` 

---
## 帮助命令
`/colorhelp` - 显示此帮助信息

# :speech_balloon: 支持平台
理论支持QQ平台，目前仅测试了napcat，因为我只有这一个平台的实例。