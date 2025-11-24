import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import textwrap  # 用于文字自动换行

# ================= 配置区域 =================
DEFAULT_FONT_NAME = "font.ttf" 

# 🎨 扇贝风格配色方案
COLOR_BG = (245, 247, 250)       # 浅灰背景
COLOR_CARD = (255, 255, 255)     # 白卡片
COLOR_ACCENT = (46, 204, 113)    # 标志性薄荷绿
COLOR_TEXT_MAIN = (51, 51, 51)   # 主黑字
COLOR_TEXT_SUB = (153, 153, 153) # 浅灰字
COLOR_COUNTDOWN = (240, 240, 240)# 背景超淡大数字

st.set_page_config(page_title="仿APP背单词视频生成器", layout="wide")
st.title("📱 仿扇贝风格背单词生成器 (修复完整版)")

# ================== 侧边栏：素材配置 ==================
st.sidebar.header("⚙️ 第一步：素材配置")

# 1. 字体逻辑 (防报错核心)
current_font_path = None
if os.path.exists(DEFAULT_FONT_NAME):
    st.sidebar.success(f"✅ 已自动加载: {DEFAULT_FONT_NAME}")
    current_font_path = DEFAULT_FONT_NAME
else:
    st.sidebar.warning(f"⚠️ 仓库未找到 {DEFAULT_FONT_NAME}，请手动上传！")

# 允许临时上传字体
uploaded_font = st.sidebar.file_uploader("上传字体 (推荐圆体/黑体)", type=["ttf", "ttc"])
if uploaded_font:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name
        st.sidebar.success("✅ 临时字体已加载")

# 2. 倒计时音效
tick_file = st.sidebar.file_uploader("上传倒计时音效 (Tick.mp3)", type=["mp3", "wav"])

st.divider()

# ================== 主界面：内容输入 ==================
st.header("📝 第二步：输入单词")
col1, col2 = st.columns(2)
with col1:
    word
