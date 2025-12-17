import re
import math
import time
import aiohttp
import asyncio
import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from collections import defaultdict

@register(
    "ColorConverter",
    "CecilyGao",
    "颜色值转换插件",
    "实现RGB、CMYK、16进制颜色值的相互转换",
    "1.4.0",
    "https://github.com/CecilyGao/astrbot_plugin_color_converter"
)
class ColorConverterPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config
        
        # 初始化白名单
        self.private_whitelist = set()
        self.group_whitelist = set()
        
        # 加载配置
        self._load_config()
        
        # 帮助信息
        self.help_text = (
            "=== 颜色值转换插件帮助 ===\n"
            "【命令格式】color <目标格式> <现有格式>\n"
            "  » 示例: color rgb 72C0FF\n"
            "  » 示例: color cmyk 114,166,255\n"
            "  » 示例: color hex 55,35,0,0\n\n"
            
            "【参数说明】\n"
            " <目标格式>: 想要转换成的格式，可选值: rgb, hex, cmyk\n"
            " <现有格式>: 现有的颜色值，支持以下格式:\n"
            "   - 16进制: 3位或6位16进制数，不需要#\n"
            "      示例: F00 (红色) 或 FF0000 (红色)\n"
            "   - RGB: 3个0-255的数字，用逗号或空格分隔\n"
            "      示例: 255,0,0 或 255 0 0\n"
            "   - CMYK: 4个0-100的数字，用逗号或空格分隔\n"
            "      示例: 0,100,100,0 (红色)\n\n"
            
            "【帮助命令】colorhelp：显示此帮助信息"
        )
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 私聊白名单
            if self.config and hasattr(self.config, 'get'):
                private_list = self.config.get('private_whitelist', [])
                if isinstance(private_list, list):
                    self.private_whitelist = set(map(str, private_list))
                
                # 群聊白名单
                group_list = self.config.get('group_whitelist', [])
                if isinstance(group_list, list):
                    self.group_whitelist = set(map(str, group_list))
                
                logger.info(f"颜色转换插件配置已加载: 私聊白名单{len(self.private_whitelist)}个, 群聊白名单{len(self.group_whitelist)}个")
                
        except Exception as e:
            logger.error(f"加载配置时发生错误: {e}")
    
    def _check_permission(self, event: AstrMessageEvent) -> tuple[bool, str]:
        """
        检查用户是否有权限使用插件
        返回: (是否允许, 错误信息)
        """
        user_id = str(event.user_id)
        
        # 检查是否在私聊中
        if event.message_type == "private":
            # 检查私聊白名单
            if self.private_whitelist and user_id not in self.private_whitelist:
                return False, "您不在私聊白名单中，无法使用此功能"
        
        # 检查是否在群聊中
        elif event.message_type == "group":
            group_id = str(event.group_id)
            # 检查群聊白名单
            if self.group_whitelist and group_id not in self.group_whitelist:
                return False, "本群不在白名单中，无法使用此功能"
        
        return True, ""
    
    @staticmethod
    def rgb_to_hex(r, g, b):
        """RGB转16进制"""
        # 验证输入值
        try:
            r = int(r)
            g = int(g)
            b = int(b)
        except ValueError:
            return None, "RGB值必须是整数"
        
        # 检查范围
        if any(not (0 <= x <= 255) for x in (r, g, b)):
            return None, "RGB值必须在0-255范围内"
        
        # 转换为16进制
        hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()
        return hex_color, None
    
    @staticmethod
    def hex_to_rgb(hex_color):
        """16进制转RGB"""
        hex_color = hex_color.strip().lstrip('#')
        
        # 验证格式
        if len(hex_color) == 3:
            # 处理缩写形式如 fff
            hex_color = ''.join(c * 2 for c in hex_color)
        
        if len(hex_color) != 6 or not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
            return None, "无效的16进制颜色值"
        
        # 解析RGB值
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            return None, "无效的16进制颜色值"
        
        return (r, g, b), None
    
    @staticmethod
    def rgb_to_cmyk(r, g, b):
        """RGB转CMYK"""
        # 验证输入值
        try:
            r = int(r)
            g = int(g)
            b = int(b)
        except ValueError:
            return None, "RGB值必须是整数"
        
        # 检查范围
        if any(not (0 <= x <= 255) for x in (r, g, b)):
            return None, "RGB值必须在0-255范围内"
        
        # 归一化到0-1
        r_prime, g_prime, b_prime = r/255.0, g/255.0, b/255.0
        
        # 计算CMYK
        k = 1 - max(r_prime, g_prime, b_prime)
        
        if abs(k - 1.0) < 0.000001:  # 纯黑色（考虑浮点误差）
            c = m = y = 0.0
        else:
            c = (1 - r_prime - k) / (1 - k)
            m = (1 - g_prime - k) / (1 - k)
            y = (1 - b_prime - k) / (1 - k)
        
        # 返回0-100的百分比值，保留两位小数
        return (
            round(c * 100, 2),
            round(m * 100, 2),
            round(y * 100, 2),
            round(k * 100, 2)
        ), None
    
    @staticmethod
    def cmyk_to_rgb(c, m, y, k):
        """CMYK转RGB"""
        # 验证输入值
        try:
            c = float(c)
            m = float(m)
            y = float(y)
            k = float(k)
        except ValueError:
            return None, "CMYK值必须是数字"
        
        # 检查范围
        if any(not (0 <= x <= 100) for x in (c, m, y, k)):
            return None, "CMYK值必须在0-100范围内"
        
        # 转换为0-1的小数
        c, m, y, k = c/100.0, m/100.0, y/100.0, k/100.0
        
        # 计算RGB
        r = 255 * (1 - c) * (1 - k)
        g = 255 * (1 - m) * (1 - k)
        b = 255 * (1 - y) * (1 - k)
        
        # 四舍五入并确保在0-255范围内
        r = max(0, min(255, int(round(r))))
        g = max(0, min(255, int(round(g))))
        b = max(0, min(255, int(round(b))))
        
        return (r, g, b), None
    
    @staticmethod
    def cmyk_to_hex(c, m, y, k):
        """CMYK转16进制"""
        rgb_result, error = ColorConverterPlugin.cmyk_to_rgb(c, m, y, k)
        if error:
            return None, error
        
        hex_result, error = ColorConverterPlugin.rgb_to_hex(*rgb_result)
        if error:
            return None, error
        
        return hex_result, None
    
    @staticmethod
    def hex_to_cmyk(hex_color):
        """16进制转CMYK"""
        rgb_result, error = ColorConverterPlugin.hex_to_rgb(hex_color)
        if error:
            return None, error
        
        cmyk_result, error = ColorConverterPlugin.rgb_to_cmyk(*rgb_result)
        if error:
            return None, error
        
        return cmyk_result, None
    
    def _detect_color_format(self, color_str: str) -> tuple[str, list]:
        """
        智能检测颜色格式
        返回: (格式类型, 数值列表)
        格式类型: 'hex', 'rgb', 'cmyk', 'unknown'
        """
        color_str = color_str.strip().replace('，', ',')  # 中文逗号转英文逗号
        
        # 1. 检测16进制格式 (3位或6位，不需要#)
        hex_str = color_str.lstrip('#')
        if re.match(r'^[0-9A-Fa-f]{3}$', hex_str) or re.match(r'^[0-9A-Fa-f]{6}$', hex_str):
            return 'hex', [hex_str]
        
        # 2. 检测逗号分隔或空格分隔的数字格式
        # 替换连续空格为单个逗号，然后分割
        normalized_str = re.sub(r'\s+', ',', color_str)
        parts = [p.strip() for p in normalized_str.split(',') if p.strip()]
        
        if not parts:
            return 'unknown', []
        
        # 尝试转换为数字
        try:
            nums = []
            for part in parts:
                # 检查是否为整数或小数
                if '.' in part:
                    nums.append(float(part))
                else:
                    nums.append(int(part))
        except ValueError:
            return 'unknown', []
        
        # 3. 根据数字数量判断格式
        if len(nums) == 3:
            # 检查是否为RGB (0-255) 或 CMYK (0-100)
            if all(0 <= n <= 255 for n in nums):
                # 如果有值大于100，很可能是RGB
                if any(n > 100 for n in nums):
                    return 'rgb', nums
                else:
                    # 值都在0-100之间，可能是RGB也可能是CMYK
                    # 检查是否为整数，RGB通常是整数
                    if all(isinstance(n, int) for n in nums):
                        return 'rgb', nums  # 优先返回rgb
                    else:
                        return 'cmyk', nums  # 有小数，更可能是cmyk
            else:
                # 有值不在0-255范围内
                if all(0 <= n <= 100 for n in nums):
                    return 'cmyk', nums
                else:
                    return 'unknown', nums
        elif len(nums) == 4:
            # 检查是否为CMYK (0-100)
            if all(0 <= n <= 100 for n in nums):
                return 'cmyk', nums
            else:
                return 'unknown', nums
        else:
            return 'unknown', nums
    
    def _convert_color(self, target_format: str, color_str: str) -> tuple[dict, str]:
        """
        转换颜色格式
        返回: (颜色信息字典, 错误信息)
        """
        # 检测输入格式
        src_format, nums = self._detect_color_format(color_str)
        
        if src_format == 'unknown':
            return {}, f"无法识别颜色格式: {color_str}\n\n支持的格式:\n- 16进制: 3位或6位(如 FF0000 或 F00)\n- RGB: 3个0-255的数字(如 255,0,0)\n- CMYK: 4个0-100的数字(如 0,100,100,0)"
        
        color_info = {}
        
        try:
            if src_format == 'hex':
                hex_str = nums[0]
                rgb, error = self.hex_to_rgb(hex_str)
                if error:
                    return {}, error
                
                cmyk, error = self.rgb_to_cmyk(*rgb)
                if error:
                    return {}, error
                
                # 生成完整的16进制表示
                if len(hex_str) == 6:
                    full_hex = f"#{hex_str.upper()}"
                else:  # 3位缩写
                    full_hex = f"#{hex_str.upper()[0]*2}{hex_str.upper()[1]*2}{hex_str.upper()[2]*2}"
                
                color_info = {
                    'hex': full_hex,
                    'rgb': rgb,
                    'cmyk': cmyk
                }
                
            elif src_format == 'rgb':
                r, g, b = nums
                hex_color, error = self.rgb_to_hex(r, g, b)
                if error:
                    return {}, error
                
                cmyk, error = self.rgb_to_cmyk(r, g, b)
                if error:
                    return {}, error
                
                color_info = {
                    'hex': hex_color,
                    'rgb': (r, g, b),
                    'cmyk': cmyk
                }
                
            elif src_format == 'cmyk':
                if len(nums) == 3:
                    # 如果是3个值，假设K=0
                    c, m, y = nums
                    k = 0
                else:
                    c, m, y, k = nums
                
                rgb, error = self.cmyk_to_rgb(c, m, y, k)
                if error:
                    return {}, error
                
                hex_color, error = self.rgb_to_hex(*rgb)
                if error:
                    return {}, error
                
                color_info = {
                    'hex': hex_color,
                    'rgb': rgb,
                    'cmyk': (c, m, y, k) if len(nums) == 4 else (c, m, y, 0)
                }
        
        except Exception as e:
            return {}, f"转换过程中发生错误: {str(e)}"
        
        # 根据目标格式返回相应结果
        result = {}
        if target_format == 'hex':
            result = {'hex': color_info['hex']}
        elif target_format == 'rgb':
            result = {'rgb': color_info['rgb']}
        elif target_format == 'cmyk':
            result = {'cmyk': color_info['cmyk']}
        
        # 添加源格式信息用于显示
        result['_src_format'] = src_format
        result['_full_info'] = color_info
        
        return result, ""
    
    def _format_output(self, color_info, target_format: str):
        """格式化输出"""
        # 提取完整颜色信息
        full_info = color_info.get('_full_info', {})
        src_format = color_info.get('_src_format', 'unknown')
        
        output = []
        output.append(f"转换结果: {src_format.upper()} → {target_format.upper()}")
        
        if color_info.get('hex'):
            output.append(f"16进制: {color_info['hex']}")
        if color_info.get('rgb'):
            r, g, b = color_info['rgb']
            output.append(f"RGB: RGB({r}, {g}, {b})")
        if color_info.get('cmyk'):
            c, m, y, k = color_info['cmyk']
            output.append(f"CMYK: CMYK({c}%, {m}%, {y}%, {k}%)")
        
        # 添加其他格式信息
        if full_info:
            other_formats = []
            if target_format != 'hex' and full_info.get('hex'):
                other_formats.append(f"16进制: {full_info['hex']}")
            if target_format != 'rgb' and full_info.get('rgb'):
                r, g, b = full_info['rgb']
                other_formats.append(f"RGB: RGB({r}, {g}, {b})")
            if target_format != 'cmyk' and full_info.get('cmyk'):
                c, m, y, k = full_info['cmyk']
                other_formats.append(f"CMYK: CMYK({c}%, {m}%, {y}%, {k}%)")
            
            if other_formats:
                output.append("")
                output.append("其他格式:")
                output.extend(other_formats)
        
        return "\n".join(output)
    
    @filter.command("color")
    async def color_converter(
        self,
        event: AstrMessageEvent,
        target_format: str = None,
        color_str: str = None,
        *args
    ):
        """
        颜色值转换命令
        用法: color <目标格式> <现有格式>
        示例: color rgb 72C0FF
        示例: color hex 114,166,255
        示例: color cmyk 55,35,0,0
        """
        # 检查权限
        allowed, error_msg = self._check_permission(event)
        if not allowed:
            yield event.plain_result(f"权限不足: {error_msg}")
            return
        
        # 如果没有提供参数，显示简单帮助
        if not target_format:
            yield event.plain_result("颜色转换插件\n使用方式: color <目标格式> <现有格式>\n示例: color rgb 72C0FF\n输入 colorhelp 查看详细帮助")
            return
        
        target_format = target_format.lower()
        
        # 验证目标格式
        if target_format not in ['rgb', 'hex', 'cmyk']:
            yield event.plain_result(f"错误：未知的目标格式 '{target_format}'，必须是 rgb, hex 或 cmyk\n\n输入 colorhelp 查看帮助")
            return
        
        # 检查是否有颜色字符串
        if not color_str:
            yield event.plain_result(f"错误：请提供颜色值\n\n示例: color {target_format} 72C0FF")
            return
        
        # 如果有额外参数，合并到颜色字符串中
        if args:
            color_str = f"{color_str} {' '.join(args)}"
        
        # 转换颜色
        color_info, error_msg = self._convert_color(target_format, color_str)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 格式化输出
        output = self._format_output(color_info, target_format)
        
        yield event.plain_result(output)
    
    @filter.command("colorhelp")
    async def color_help(self, event: AstrMessageEvent):
        """显示颜色转换帮助信息"""
        allowed, error_msg = self._check_permission(event)
        if not allowed:
            yield event.plain_result(f"权限不足: {error_msg}")
            return
        
        yield event.plain_result(self.help_text)
    
    async def terminate(self):
        """清理资源"""
        logger.info("颜色转换插件正在关闭...")