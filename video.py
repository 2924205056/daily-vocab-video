import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import textwrap

# ================= 1. 基础配置 =================
DEFAULT_FONT_NAME = "font.ttf" 

# 扇贝单词配色方案
COLOR_BG = (245, 247, 250)
COLOR_CARD = (255, 255, 255)
COLOR_ACCENT = (46, 204, 113)    # 绿色
COLOR_TEXT_MAIN = (51, 51, 51)   # 深灰
COLOR_TEXT_SUB = (153, 153, 153) # 浅灰
COLOR_COUNTDOWN = (240, 240, 240)# 淡灰

st.set_page_config(page_title="仿扇贝视频生成器", layout="wide")
st.title("📱 仿扇贝风格背单词生成器")

# ================== 2. 侧边栏配置 ==================
st.sidebar.header("⚙️ 素材配置")

# 字体加载逻辑
current_font_path = None
if os.path.exists(DEFAULT_FONT_NAME):
    st.sidebar.success(f"✅ 已加载字体: {DEFAULT_FONT_NAME}")
    current_font_path = DEFAULT_FONT_NAME
else:
    st.sidebar.warning(f"⚠️ 仓库未找到 {DEFAULT_FONT_NAME}，请手动上传！")

uploaded_font = st.sidebar.file_uploader("上传字体 (.ttf)", type=["ttf", "ttc"])
if uploaded_font:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name
        st.sidebar.success("✅ 临时字体已加载")

tick_file = st.sidebar.file_uploader("上传倒计时音效 (.mp3)", type=["mp3", "wav"])

st.divider()

# ================== 3. 输入区域 (关键：要在函数之前) ==================
st.header("📝 输入单词信息")
col1, col2 = st.columns(2)

# 左侧输入
word = col1.text_input("单词", value="ambiguous")
ipa = col1.text_input("音标", value="/æmˈbɪɡjuəs/")
meaning = col1.text_input("中文释义", value="adj. 模棱两可的；含糊不清的")

# 右侧输入
sentence = col2.text_area("英文例句", value="His role has always been ambiguous.")
translation = col2.text_input("例句翻译", value="他的角色一直模棱两可。")

# ================== 4. 绘图与视频处理函数 ==================

def draw_text_wrapped(draw, text, font, color, x, y, max_width, line_spacing=10):
    """文本自动换行绘制"""
    try:
        bbox = draw.textbbox((0, 0), "A", font=font)
        char_width = bbox[2] - bbox[0]
    except:
        char_width = 20 # 降级处理
        
    if char_width == 0: char_width = 10 
    
    chars_per_line = int(max_width / char_width)
    if chars_per_line < 1: chars_per_line = 1
    
    lines = textwrap.wrap(text, width=chars_per_line)
    
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=color)
        bbox_line = draw.textbbox((0, 0), line, font=font)
        line_height = bbox_line[3] - bbox_line[1]
        current_y += line_height + line_spacing
    return current_y

def draw_app_interface(data, font_path, mode="countdown", countdown_num=3):
    """绘制单帧画面"""
    W, H = 1080, 1920
    img = Image.new('RGB', (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    # 字体加载 (防报错)
    try:
        if not font_path: raise Exception("No font")
        font_huge = ImageFont.truetype(font_path, 130)
        font_big = ImageFont.truetype(font_path, 80)
        font_mid = ImageFont.truetype(font_path, 60)
        font_small = ImageFont.truetype(font_path, 50)
        font_giant = ImageFont.truetype(font_path, 700)
    except:
        default = ImageFont.load_default()
        font_huge = font_big = font_mid = font_small =
