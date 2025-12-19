# main.py - 颜色转换插件完整修复版本
import re
import aiohttp
from PIL import Image, ImageDraw
from io import BytesIO
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.api.message_components import Reply, Image as ImgComponent

@register(
    "Color",
    "CecilyGao",
    "实现RGB、CMYK、16进制颜色值的相互转换，以及图片取色功能",
    "1.0.2",
    "https://github.com/CecilyGao/astrbot_plugin_color"
)
class ColorConverterPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        # 确保config不为None
        self.config = config or {}
        
        # 初始化白名单
        self.private_whitelist = set()
        self.group_whitelist = set()
        
        # 初始化HTTP会话
        self.session = None
        
        # 加载配置
        self._load_config()
        
        # 更新帮助信息，包含取色器功能
        self.help_text = (
            "=== 颜色值转换插件帮助 ===\n"
            "【命令格式】color <目标格式> <颜色值>\n"
            "  » 示例: color rgb 72C0FF\n"
            "  » 示例: color cmyk 114,166,255\n"
            "  » 示例: color hex 55,35,0,0\n\n"
            
            "【参数说明】\n"
            " <目标格式>: 想要转换成的格式，可选值: rgb hex cmyk\n"
            " <颜色值>: 现有的颜色值，支持以下格式:\n"
            "   - 16进制: 3位或6位16进制数，不需要#\n"
            "      示例: F00 (红色) 或 FF0000 (红色)\n"
            "   - RGB: 3个0-255的数字，用逗号分隔\n"
            "      示例: 255,0,0 (红色)\n"
            "   - CMYK: 4个0-100的数字，用逗号分隔\n"
            "      示例: 0,100,100,0 (红色)\n\n"
            
            "【取色器命令】\n"
            "命令格式: color pick <坐标> （需要引用一张图片）\n"
            "  » 示例: （引用一张3840*2160图片）color pick 1490,532\n"
            "  说明: 引用一张图片，回复该图片上指定坐标(x,y)的颜色值\n"
            "  坐标格式: x,y (例如: 1490,532)\n\n"
            
            "【帮助命令】colorhelp：显示此帮助信息"
        )
    
    async def _ensure_session(self):
        """确保HTTP会话已创建"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _get_image_from_event(self, event: AstrMessageEvent) -> bytes | None:
        """
        从事件中获取图片
        参考main1.py的处理方式
        """
        img_bytes_list = []
        
        # 检查消息中的每个组件
        for seg in event.message_obj.message:
            # 处理回复消息中的图片
            if isinstance(seg, Reply) and seg.chain:
                for s_chain in seg.chain:
                    if isinstance(s_chain, ImgComponent):
                        # 优先使用url，如果url不存在则使用file
                        if s_chain.url:
                            img_bytes = await self._download_image(s_chain.url)
                            if img_bytes:
                                img_bytes_list.append(img_bytes)
                        elif s_chain.file:
                            # 如果是本地文件，读取文件
                            try:
                                with open(s_chain.file, 'rb') as f:
                                    img_bytes_list.append(f.read())
                            except Exception as e:
                                logger.error(f"读取图片文件失败: {e}")
            
            # 处理当前消息中的图片
            elif isinstance(seg, ImgComponent):
                if seg.url:
                    img_bytes = await self._download_image(seg.url)
                    if img_bytes:
                        img_bytes_list.append(img_bytes)
                elif seg.file:
                    try:
                        with open(seg.file, 'rb') as f:
                            img_bytes_list.append(f.read())
                    except Exception as e:
                        logger.error(f"读取图片文件失败: {e}")
        
        # 返回第一张图片，如果没有图片则返回None
        return img_bytes_list[0] if img_bytes_list else None
    
    async def _download_image(self, url: str) -> bytes | None:
        """下载图片"""
        await self._ensure_session()
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logger.warning(f"无法下载图片 (状态: {resp.status}) URL: {url}")
                    return None
        except Exception as e:
            logger.error(f"下载图片时发生错误: {e}")
            return None
    
    def _create_color_preview_image(self, r: int, g: int, b: int) -> BytesIO:
        """创建颜色预览小图"""
        # 创建100x100的图片
        size = 100
        image = Image.new('RGB', (size, size), (r, g, b))
        
        # 添加边框
        draw = ImageDraw.Draw(image)
        border_width = 2
        draw.rectangle(
            [0, 0, size-1, size-1],
            outline=(200, 200, 200),
            width=border_width
        )
        
        # 添加文本标签
        draw.text(
            (size//2, size//2),
            f"#{r:02x}{g:02x}{b:02x}".upper(),
            fill=(255, 255, 255) if (r*0.299 + g*0.587 + b*0.114) < 128 else (0, 0, 0),
            anchor="mm"
        )
        
        # 转换为BytesIO
        bio = BytesIO()
        image.save(bio, format='PNG')
        bio.seek(0)
        return bio
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 私聊白名单
            private_list = self.config.get('private_whitelist', [])
            if isinstance(private_list, list):
                self.private_whitelist = set(map(str, private_list))
                logger.info(f"私聊白名单加载: {len(self.private_whitelist)}个用户")
            else:
                logger.warning(f"私聊白名单配置格式错误，期望列表类型，实际: {type(private_list)}")
                self.private_whitelist = set()
            
            # 群聊白名单
            group_list = self.config.get('group_whitelist', [])
            if isinstance(group_list, list):
                self.group_whitelist = set(map(str, group_list))
                logger.info(f"群聊白名单加载: {len(self.group_whitelist)}个群组")
            else:
                logger.warning(f"群聊白名单配置格式错误，期望列表类型，实际: {type(group_list)}")
                self.group_whitelist = set()
            
            if not self.private_whitelist and not self.group_whitelist:
                logger.info("未配置白名单，插件将对所有用户和群组开放")
            else:
                logger.info(f"颜色转换插件配置已加载: 私聊白名单{len(self.private_whitelist)}个, 群聊白名单{len(self.group_whitelist)}个")
                
        except Exception as e:
            logger.error(f"加载配置时发生错误: {e}")
            # 初始化空白名单
            self.private_whitelist = set()
            self.group_whitelist = set()
            logger.info("使用默认空白名单配置")
    
    def _get_user_id(self, event: AstrMessageEvent) -> str:
        """从事件中获取用户ID - 使用标准API"""
        try:
            user_id = event.get_sender_id()
            return str(user_id) if user_id else ""
        except Exception as e:
            logger.warning(f"获取用户ID时发生错误: {e}")
            return ""
    
    def _get_group_id(self, event: AstrMessageEvent) -> str:
        """从事件中获取群组ID - 使用标准API"""
        try:
            group_id = event.get_group_id()
            return str(group_id) if group_id else ""
        except Exception as e:
            logger.warning(f"获取群组ID时发生错误: {e}")
            return ""
    
    def _get_message_type(self, event: AstrMessageEvent) -> str:
        """获取消息类型 - 使用标准API"""
        try:
            message_type = event.get_message_type()
            return str(message_type) if message_type else ""
        except Exception as e:
            logger.warning(f"获取消息类型时发生错误: {e}")
            return ""
    
    def _check_permission(self, event: AstrMessageEvent) -> tuple[bool, str]:
        """
        检查用户是否有权限使用插件
        返回: (是否允许, 错误信息)
        """
        # 获取消息类型
        message_type = self._get_message_type(event)
        
        # 如果是私聊，检查私聊白名单
        if message_type == "private":
            if not self.private_whitelist:
                # 如果没有设置白名单，默认允许
                return True, ""
            
            user_id = self._get_user_id(event)
            if not user_id:
                return False, "无法获取用户信息，请稍后重试"
            
            if user_id not in self.private_whitelist:
                return False, "您不在私聊白名单中，无法使用此功能"
        
        # 如果是群聊，检查群聊白名单
        elif message_type == "group":
            if not self.group_whitelist:
                # 如果没有设置白名单，默认允许
                return True, ""
            
            group_id = self._get_group_id(event)
            if not group_id:
                return False, "无法获取群组信息，请稍后重试"
            
            if group_id not in self.group_whitelist:
                return False, "本群不在白名单中，无法使用此功能"
        
        # 其他情况默认允许
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
        
        # 使用更清晰的方式检查纯黑色
        if k > 0.999999:  # 接近1.0时视为纯黑色
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
        
        # 2. 检测逗号分隔的数字格式
        parts = [p.strip() for p in color_str.split(',') if p.strip()]
        
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
            # RGB格式：3个值，范围0-255
            if all(0 <= n <= 255 for n in nums):
                return 'rgb', nums
            else:
                return 'unknown', nums
        elif len(nums) == 4:
            # CMYK格式：4个值，范围0-100
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
                # CMYK必须是4个值
                if len(nums) != 4:
                    return {}, "CMYK格式需要4个值，用逗号分隔 (如: 0,100,100,0)"
                
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
                    'cmyk': (c, m, y, k)
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
    
    async def _pick_color_from_image(self, image_bytes: bytes, coord_str: str) -> tuple[dict, str]:
        """
        从图片中拾取颜色
        返回: (颜色信息字典, 错误信息)
        """
        try:
            # 解析坐标
            coord_str = coord_str.strip().replace('，', ',')  # 中文逗号转英文逗号
            coord_parts = coord_str.split(',')
            
            if len(coord_parts) != 2:
                return {}, "坐标格式错误，请输入 x,y 格式的坐标（例如: 1490,532）"
            
            try:
                x = int(coord_parts[0].strip())
                y = int(coord_parts[1].strip())
            except ValueError:
                return {}, "坐标必须是整数"
            
            # 加载图片
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            width, height = image.size
            
            # 检查坐标是否在图片范围内
            if x < 0 or x >= width or y < 0 or y >= height:
                return {}, f"坐标 ({x},{y}) 超出图片范围 (图片尺寸: {width}x{height})"
            
            # 获取颜色
            pixel = image.getpixel((x, y))
            r, g, b = pixel
            
            # 转换为各种格式
            hex_color, error = self.rgb_to_hex(r, g, b)
            if error:
                return {}, error
            
            cmyk, error = self.rgb_to_cmyk(r, g, b)
            if error:
                return {}, error
            
            return {
                'hex': hex_color,
                'rgb': (r, g, b),
                'cmyk': cmyk,
                '_image_size': (width, height),
                '_coord': (x, y)
            }, ""
            
        except Exception as e:
            logger.error(f"取色时发生错误: {e}", exc_info=True)
            return {}, f"取色时发生错误: {str(e)}"
    
    def _format_pick_output(self, color_info: dict) -> tuple[str, BytesIO]:
        """格式化取色器输出，返回文本和预览图片"""
        output = []
        
        # 基本信息
        x, y = color_info.get('_coord', (0, 0))
        width, height = color_info.get('_image_size', (0, 0))
        
        output.append(f"图片取色结果 (图片尺寸: {width}x{height}, 坐标: ({x},{y}))")
        output.append("")
        
        # 颜色值
        if color_info.get('hex'):
            output.append(f"16进制: {color_info['hex']}")
        
        if color_info.get('rgb'):
            r, g, b = color_info['rgb']
            output.append(f"RGB: RGB({r}, {g}, {b})")
        
        if color_info.get('cmyk'):
            c, m, y, k = color_info['cmyk']
            output.append(f"CMYK: CMYK({c}%, {m}%, {y}%, {k}%)")
        
        # 生成颜色预览图片
        r, g, b = color_info['rgb']
        preview_image = self._create_color_preview_image(r, g, b)
        
        return "\n".join(output), preview_image
    
    @filter.command("color")
    async def color_converter(self, event: AstrMessageEvent):
        """
        颜色值转换命令
        用法: color <目标格式> <颜色值>
        示例: color rgb 72C0FF
        示例: color hex 114,166,255
        示例: color cmyk 55,35,0,0
        """
        # 检查权限
        allowed, error_msg = self._check_permission(event)
        if not allowed:
            yield event.plain_result(f"权限不足: {error_msg}")
            return
        
        # 获取原始消息
        raw_message = ""
        try:
            # 优先使用标准API获取消息
            if hasattr(event, 'get_message_str'):
                raw_message = event.get_message_str()
            elif hasattr(event, 'raw_message'):
                raw_message = event.raw_message
        except Exception as e:
            logger.warning(f"获取原始消息时出错: {e}")
            yield event.plain_result("获取消息时出错，请重试")
            return
        
        # 如果没有原始消息，返回帮助
        if not raw_message:
            yield event.plain_result("颜色转换插件\n使用方式: color <目标格式> <颜色值>\n示例: color rgb 72C0FF\n输入 colorhelp 查看详细帮助")
            return
        
        # 去除命令前缀
        command_prefix = "color"
        if raw_message.startswith(command_prefix):
            content = raw_message[len(command_prefix):].strip()
        else:
            # 如果不是以color开头，可能是其他方式触发，使用整个消息
            content = raw_message
        
        # 如果没有内容，显示帮助
        if not content:
            yield event.plain_result("颜色转换插件\n使用方式: color <目标格式> <颜色值>\n示例: color rgb 72C0FF\n输入 colorhelp 查看详细帮助")
            return
        
        # 检查是否为pick命令
        if 'pick' in content.lower():
            # pick命令需要特殊处理：color pick x,y
            parts = content.strip().split(maxsplit=2)
        else:
            # 普通颜色转换命令：只需要分割成2部分
            parts = content.strip().split(maxsplit=1)
        
        if len(parts) < 1:
            yield event.plain_result("颜色转换插件\n使用方式: color <目标格式> <颜色值>\n示例: color rgb 72C0FF\n输入 colorhelp 查看详细帮助")
            return
        
        command_type = parts[0].lower()
        
        # 处理pick命令
        if command_type == 'pick':
            if len(parts) < 2:
                yield event.plain_result("错误：请提供坐标\n\n格式: color pick x,y\n示例: color pick 1490,532 (需要引用图片)")
                return
            
            coord_str = parts[1]
            
            # 获取图片
            image_bytes = await self._get_image_from_event(event)
            if not image_bytes:
                yield event.plain_result("错误：请引用一张图片进行取色\n\n用法: 引用一张图片并发送 color pick x,y\n示例: 引用图片后发送 color pick 1490,532")
                return
            
            # 取色
            color_info, error_msg = await self._pick_color_from_image(image_bytes, coord_str)
            if error_msg:
                yield event.plain_result(error_msg)
                return
            
            # 格式化输出并生成预览图片
            text_output, preview_image = self._format_pick_output(color_info)
            
            # 使用消息链发送文本和图片
            chain = [
                Comp.Plain(text_output),
                Comp.Plain(" \n"),
                Comp.Plain("颜色预览:\n"),
                Comp.Image.fromBytes(preview_image.getvalue())
            ]
            
            yield event.chain_result(chain)
            return
        
        # 处理传统的颜色转换命令
        if len(parts) < 2:
            if command_type in ['rgb', 'hex', 'cmyk']:
                yield event.plain_result(f"错误：请提供颜色值\n\n示例: color {command_type} 72C0FF")
            else:
                yield event.plain_result(f"错误：命令格式不正确\n\n正确格式: color <目标格式> <颜色值>\n示例: color rgb 72C0FF")
            return
        
        target_format = command_type
        color_str = parts[1]
        
        # 验证目标格式
        if target_format not in ['rgb', 'hex', 'cmyk']:
            yield event.plain_result(f"错误：未知的目标格式 '{target_format}'，必须是 rgb, hex 或 cmyk\n\n输入 colorhelp 查看帮助")
            return
        
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
        # 直接显示帮助信息，不进行复杂的权限检查
        yield event.plain_result(self.help_text)
    
    async def terminate(self):
        """清理资源"""
        logger.info("颜色转换插件正在关闭...")
        if self.session:
            await self.session.close()
            logger.info("HTTP会话已关闭")