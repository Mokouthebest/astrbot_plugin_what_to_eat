import os
import json
import random
from PIL import Image as PILImage, ImageDraw, ImageFont

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image

@register("whateat_pic", "AstrBotUser", "今天吃什么图片版适配", "1.0.0")
class WhatEatPicPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 定义插件所在的目录
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 创建资源文件夹 (存放原仓库的图片、字体和菜单)
        self.res_dir = os.path.join(self.plugin_dir, "resources")
        if not os.path.exists(self.res_dir):
            os.makedirs(self.res_dir)
            
        # 兜底的默认菜单（如果没提供 json 文件就会用这个）
        self.default_foods = ["麻辣烫", "兰州拉面", "黄焖鸡米饭", "沙县小吃", "肯德基", "麦当劳", "火锅", "烤肉", "炒饭", "汉堡王", "螺蛳粉", "水饺"]
        self.default_drinks = ["奶茶", "可乐", "雪碧", "咖啡", "矿泉水", "柠檬水", "果汁", "啤酒"]

    def get_menu(self, is_drink=False):
        """读取菜单，你可以把原仓库的 json 数据放到 resources/menu.json 下"""
        json_path = os.path.join(self.res_dir, "menu.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("drinks" if is_drink else "foods", self.default_drinks if is_drink else self.default_foods)
            except Exception as e:
                print(f"读取菜单失败: {e}")
        return self.default_drinks if is_drink else self.default_foods

    def draw_image(self, text: str) -> str:
        """核心作图逻辑：把文字画到背景图上"""
        bg_path = os.path.join(self.res_dir, "bg.png")     # 请将背景图重命名为 bg.png 放入 resources
        font_path = os.path.join(self.res_dir, "font.ttf") # 请将字体文件重命名为 font.ttf 放入 resources
        
        # 检查资源是否存在，如果不存在则生成简单的纯色图兜底
        if not os.path.exists(bg_path) or not os.path.exists(font_path):
            img = PILImage.new('RGB', (500, 300), color=(255, 240, 245))
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((50, 130), f"No Assets Found!\n{text}", fill=(0, 0, 0), font=font)
        else:
            # 打开背景图
            img = PILImage.open(bg_path).convert("RGBA")
            draw = ImageDraw.Draw(img)
            
            # 加载字体（字号设为 60，可根据你的背景图自行调整）
            font = ImageFont.truetype(font_path, 60) 
            
            # 让文字居中
            img_w, img_h = img.size
            # 获取文字的包围盒 (Pillow >= 8.0.0)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            x = (img_w - text_w) / 2
            y = (img_h - text_h) / 2 - 20 # 稍微往上提一点，视背景图而定
            
            # 画上文字，颜色设为深灰色
            draw.text((x, y), text, fill=(50, 50, 50), font=font)

        # 保存为临时文件以供发送
        output_path = os.path.join(self.plugin_dir, "temp_output.png")
        img.save(output_path)
        return output_path

    # 监听指令，使用正则匹配各种问法
    @filter.regex(r"^(早上|中午|晚上|夜宵|今天)?(吃什么|喝什么)$")
    async def handle_what_eat(self, event: AstrMessageEvent):
        msg_text = event.message_obj.message_str
        
        # 判断是吃还是喝
        is_drink = "喝什么" in msg_text
        action = "喝" if is_drink else "吃"
        
        # 随机抽取
        menu = self.get_menu(is_drink)
        choice = random.choice(menu)
            
        # 提取时间词
        time_word = "今天"
        for t in ["早上", "中午", "晚上", "夜宵"]:
            if t in msg_text:
                time_word = t
                break

        # 拼接文案
        final_text = f"{time_word}{action} {choice}！"
        
        # 调用作图
        image_path = self.draw_image(final_text)
        
        # 使用 AstrBot 的标准 API 发送生成的图片
        yield event.plain_result().add_image(image_path)
