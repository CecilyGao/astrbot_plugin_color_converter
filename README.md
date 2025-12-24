# astrbot_plugin_color
颜色插件，支持RGB/CMYK/16进制颜色互转、图片按坐标取色、图片色板分析等功能

# 🔧 安装
方法一：使用插件市场 (推荐)

搜索 color 并安装

方法二：Git Clone

进入 AstrBot 的 data/plugins/ 目录，然后执行：

```bash
git clone https://github.com/CecilyGao/astrbot_plugin_color
```

## 安装依赖

本插件需要：
- aiohttp>=3.8.0
- pillow>=9.0.0

手动安装依赖：pip install aiohttp pillow

```bash
pip install -r requirements.txt
```

无论使用哪种方法，插件的依赖都会在机器人下次重启时自动安装。

# 🚀 使用说明
## 指令1：颜色格式转换
`color '目标格式' '颜色值'`

### 参数
- '目标格式': 想要转换成的格式，可选值: rgb, hex, cmyk
- '颜色值': 想转换的颜色值，支持以下格式:
-- 16进制: 3位或6位16进制数。示例: F00或 FF0000
-- RGB: 3个0-255的数字，用逗号分隔。示例: 255,0,0
-- CMYK: 4个0-100的数字，用逗号分隔。示例: 0,100,100,0
            
### 示例
- `color rgb 72C0FF` - 将16进制的#72C0FF转换为RGB格式
- `color cmyk 114,166,255` - 将RGB的(114,166,255)转换为CMYK格式
- `color hex 55,35,0,0` - 将CMYK的（55%,35%,0%,0%）转换成16进制格式

<img width="740" height="609" alt="IMG_579" src="https://github.com/user-attachments/assets/979cec23-7aeb-4928-9be0-ccf567e892b1" />


---
## 指令2：图片坐标取色器
`color pick '坐标' （需要引用一张图片）`

### 参数
- `坐标`: x,y 例如: 1490,532

### 示例
- `color pick 1490,532（引用一张图片）` 

<img width="760" height="1632" alt="IMG_582" src="https://github.com/user-attachments/assets/f886f0b6-b09c-4622-8049-37142b92de49" />


---
## 指令3：图片色板分析器
`color analyze '颜色数量' （需要引用一张图片）`

### 参数
- `颜色数量`：1-10，不填默认为5 例如：3

### 示例
- `color analyze 7（引用一张图片）`

## 帮助命令
`colorhelp` - 显示此帮助信息

# 🖥 支持平台
理论支持aiocqhttp，目前仅测试了napcat，因为我只有这一个平台的实例。我事插件小白不要欺负我😭

# 💡 更新情况
- v1.0.3 新增功能：color analyze色板分析
- v1.0.2 修复了bug：未能正确判断颜色值
- v1.0.1 新增功能：color pick取色器
- v1.0.0 实现颜色格式转换功能
