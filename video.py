import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os
import textwrap

# ================= 1. 基础配置 =================
DEFAULT_FONT_NAME = "font.ttf" 

# 扇贝单词配色
COLOR_BG = (245, 247, 250)
COLOR_CARD = (255, 255, 255)
COLOR_ACCENT = (46, 204, 113)
COLOR_TEXT_MAIN = (51, 51, 51)
COLOR_TEXT_SUB = (153, 153, 153)
COLOR_COUNTDOWN = (240, 240, 240)

st.set_page_config(page_title="仿扇贝视频生成器", layout="wide")
st.title("📱 仿扇贝风格背单词生成器")

# ================== 2. 侧边栏 ==================
st.sidebar.header("⚙️ 素材配置")

current_font_path = None
if os.path.exists(DEFAULT_FONT_NAME):
    st.sidebar.success(f"✅ 已加载字体: {DEFAULT_FONT_NAME}")
    current_font_path = DEFAULT_FONT_NAME
else:
    st.sidebar.warning(f"⚠️ 未找到 {DEFAULT_FONT_NAME}，请手动上传！")

uploaded_font = st.sidebar.file_uploader("上传字体 (.ttf)", type=["ttf", "ttc"])
if uploaded_font:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name
        st.sidebar.success("✅ 临时字体已加载")

tick_file = st.sidebar.file_uploader("上传倒计时音效 (.mp3)", type=["mp3", "wav"])

st.divider()

# ================== 3. 输入区 ==================
st.header("📝 输入单词信息")
col1, col2 = st.columns(2)

word = col1.text_input("单词", value="ambiguous")
ipa = col1.text_input("音标", value="/æmˈbɪɡjuəs/")
meaning = col1.text_input("中文释义", value="adj. 模棱两可的；含糊不清的")

sentence = col2.text_area("英文例句", value="His role has always been ambiguous.")
translation = col2.text_input("例句翻译", value="他的角色一直模棱两可。")

# ================== 4. 核心函数 ==================

def draw_text_wrapped(draw, text, font, color, x, y, max_width, line_spacing=10):
    """自动换行绘制"""
    try:
        bbox = draw.textbbox((0, 0), "A", font=font)
        char_width = bbox[2] - bbox[0]
    except:
        char_width = 20
        
    if char_width == 0: char_width = 10
    
    chars_per_line = int(max_width / char_width)
    if chars_per_line < 1: chars_per_line = 1
    
    lines = textwrap.wrap(text, width=chars_per_line)
    
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=color)
        bbox_line = draw.textbbox((0, 0), line, font=font)
        h = bbox_line[3] - bbox_line[1]
        current_y += h + line_spacing
    return current_y

def draw_app_interface(data, font_path, mode="countdown", countdown_num=3):
    """绘制画面"""
    W, H = 1080, 1920
    img = Image.new('RGB', (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    # 字体加载 (这里是你之前报错的地方，我拆开了)
    try:
        if not font_path: raise Exception("No font")
        font_huge = ImageFont.truetype(font_path, 130)
        font_big = ImageFont.truetype(font_path, 80)
        font_mid = ImageFont.truetype(font_path, 60)
        font_small = ImageFont.truetype(font_path, 50)
        font_giant = ImageFont.truetype(font_path, 700)
    except:
        # 如果加载失败，使用默认字体
        default = ImageFont.load_default()
        # 下面这几行我拆开了，防止复制出错
        font_huge = default
        font_big = default
        font_mid = default
        font_small = default
        font_giant = default

    # 绘制顶部
    draw.rectangle([(0, 0), (W, 180)], fill=COLOR_ACCENT) 
    draw.text((40, 60), "单词每日背", font=font_small, fill="white")
    
    # 绘制卡片
    card_margin, card_top, card_bottom = 60, 300, 1450
    draw.rectangle([(card_margin, card_top), (W-card_margin, card_bottom)], fill=COLOR_CARD)
    
    # 单词内容
    bbox_w = draw.textbbox((0, 0), data['word'], font=font_huge)
    w_w = bbox_w[2] - bbox_w[0]
    draw.text(((W - w_w)/2, card_top + 150), data['word'], font=font_huge, fill=COLOR_TEXT_MAIN)
    
    bbox_i = draw.textbbox((0, 0), data['ipa'], font=font_mid)
    i_w = bbox_i[2] - bbox_i[0]
    draw.text(((W - i_w)/2, card_top + 330), data['ipa'], font=font_mid, fill=COLOR_TEXT_SUB)

    # 模式分支
    if mode == "countdown":
        num_str = f"0{countdown_num}"
        bbox_n = draw.textbbox((0, 0), num_str, font=font_giant)
        n_w = bbox_n[2] - bbox_n[0]
        
        draw.text(((W - n_w)/2, card_top + 500), num_str, font=font_giant, fill=COLOR_COUNTDOWN)
        
        # 进度条
        bar_w = 600
        bar_x = (W - bar_w) / 2
        bar_y = card_bottom - 300
        progress = (4 - countdown_num) / 3
        
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + 20)], fill=(230,230,230))
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_w * progress, bar_y + 20)], fill=COLOR_ACCENT)
        
        tip = "三遍之后看答案"
        bbox_t = draw.textbbox((0, 0), tip, font=font_mid)
        t_w = bbox_t[2] - bbox_t[0]
        draw.text(((W - t_w)/2, bar_y + 60), tip, font=font_mid, fill=COLOR_TEXT_MAIN)

    elif mode == "result":
        content_y = card_top + 500
        
        draw.text((card_margin + 80, content_y), data['meaning'], font=font_mid, fill=COLOR_TEXT_MAIN)
        
        line_y = content_y + 120
        draw.line([(card_margin+40, line_y), (W-card_margin-40, line_y)], fill=(240,240,240), width=3)
        
        draw.text((card_margin + 80, line_y + 60), "例句:", font=font_small, fill=COLOR_ACCENT)
        
        last_y = draw_text_wrapped(draw, data['sentence'], font_small, COLOR_TEXT_MAIN, 
                                 card_margin + 80, line_y + 140, 800)
        
        draw_text_wrapped(draw, data['translation'], font_small, COLOR_TEXT_SUB, 
                        card_margin + 80, last_y + 40, 800)

    # 按钮
    btn_y = 1580
    draw.rounded_rectangle([(100, btn_y), (480, btn_y+180)], radius=40, fill=(255,235,238))
    draw.text((180, btn_y+60), "提示一下", font=font_mid, fill=(255,100,100))
    
    draw.rounded_rectangle([(W-480, btn_y), (W-100, btn_y+180)], radius=40, fill=COLOR_ACCENT)
    draw.text((W-360, btn_y+60), "我认识", font=font_mid, fill="white")

    temp_path = tempfile.mktemp(suffix=".png")
    img.save(temp_path)
    return temp_path

def process_video(font_path, tick_path, data):
    """视频生成逻辑"""
    temp_dir = tempfile.mkdtemp()
    audio_word = os.path.join(temp_dir, "word.mp3")
    audio_sent = os.path.join(temp_dir, "sentence.mp3")
    output_path = os.path.join(temp_dir, "output.mp4")

    # 1. 语音
    try:
        gTTS(text=data['word'], lang='en').save(audio_word)
        gTTS(text=data['sentence'], lang='en').save(audio_sent)
    except Exception as e:
        st.error(f"语音失败: {e}")
        return None

    clip_word = AudioFileClip(audio_word)
    clip_sent = AudioFileClip(audio_sent)
    
    clip_tick = None
    if tick_path:
        clip_tick = AudioFileClip(tick_path).subclip(0, 1).volumex(0.4)

    # 2. 倒计时片段
    intro_clips = []
    for i in [3, 2, 1]:
        img_path = draw_app_interface(data, font_path, "countdown", i)
        
        if clip_tick:
            audio_now = CompositeAudioClip([clip_word, clip_tick])
        else:
            audio_now = clip_word
            
        dur = max(1.0, audio_now.duration)
        clip = ImageClip(img_path).set_duration(dur).set_audio(audio_now)
        intro_clips.append(clip)
    
    intro_final = concatenate_videoclips(intro_clips)

    # 3. 结果片段
    res_path = draw_app_interface(data, font_path, "result")
    res_final = ImageClip(res_path).set_duration(clip_sent.duration + 2).set_audio(clip_sent)

    # 4. 合并
    final = concatenate_videoclips([intro_final, res_final])
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
    return output_path

# ================== 5. 执行 ==================

if st.button("🚀 生成视频", type="primary"):
    if not current_font_path:
        st.error("❌ 请上传字体！")
    else:
        data_pack = {
            "word": word, 
            "ipa": ipa, 
            "meaning": meaning, 
            "sentence": sentence, 
            "translation": translation
        }
        
        with st.spinner("生成中..."):
            t_tick = None
            if tick_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    f.write(tick_file.read())
                    t_tick = f.name
            
            try:
                path = process_video(current_font_path, t_tick, data_pack)
                if path:
                    st.success("✅ 完成")
                    st.video(path)
                    with open(path, "rb") as file:
                        st.download_button("下载视频", data=file, file_name="vocab.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"错误: {e}")
