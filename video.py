import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import textwrap

# ================= 1. 基础配置 =================
DEFAULT_FONT_NAME = "font.ttf" 

# 配色方案
COLOR_BG = (245, 247, 250)
COLOR_CARD = (255, 255, 255)
COLOR_ACCENT = (46, 204, 113)
COLOR_TEXT_MAIN = (51, 51, 51)
COLOR_TEXT_SUB = (153, 153, 153)
COLOR_COUNTDOWN = (240, 240, 240)

st.set_page_config(page_title="背单词视频生成器", layout="wide")
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

uploaded_font = st.sidebar.file_uploader("上传字体", type=["ttf", "ttc"])
if uploaded_font:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name
        st.sidebar.success("✅ 临时字体已加载")

tick_file = st.sidebar.file_uploader("上传倒计时音效", type=["mp3", "wav"])

st.divider()

# ================== 3. 核心：输入框 (必须在最前面!) ==================
# ⚠️ 注意：这里使用 col1.text_input 这种写法，不容易出错
st.header("📝 输入单词信息")
col1, col2 = st.columns(2)

# 左侧输入
word = col1.text_input("单词", value="ambiguous")
ipa = col1.text_input("音标", value="/æmˈbɪɡjuəs/")
meaning = col1.text_input("中文释义", value="adj. 模棱两可的；含糊不清的")

# 右侧输入
sentence = col2.text_area("英文例句", value="His role has always been ambiguous.")
translation = col2.text_input("例句翻译", value="他的角色一直模棱两可。")

# ================== 4. 功能函数定义 ==================

def draw_text_wrapped(draw, text, font, color, x, y, max
