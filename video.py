import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os

# ================= 配置区域 =================
DEFAULT_FONT_NAME = "font.ttf" 

# APP 风格配色
COLOR_BG = (245, 247, 250)      # 浅灰背景
COLOR_CARD = (255, 255, 255)    # 白卡片
COLOR_TEXT_MAIN = (51, 51, 51)  # 深黑字
COLOR_TEXT_SUB = (153, 153, 153)# 浅灰字
COLOR_ACCENT = (46, 204, 113)   # 扇贝绿
COLOR_COUNTDOWN = (230, 230, 230) # 倒计时超淡大字

st.set_page_config(page_title="仿APP背单词视频生成器", layout="wide")
st.title("📱 仿APP风格背单词生成器")

# ================== 侧边栏 ==================
st.sidebar.header("⚙️ 素材配置")

# 字体加载逻辑
current_font_path = None
if os.path.exists(DEFAULT_FONT_NAME):
    st.sidebar.success(f"✅ 已加载仓库字体: {DEFAULT_FONT_NAME}")
    current_font_path = DEFAULT_FONT_NAME
else:
    st.sidebar.warning(f"⚠️ 请上传字体文件 (font.ttf)，否则无法生成好看的界面！")

uploaded_font = st.sidebar.file_uploader("替换字体 (推荐圆体/黑体)", type=["ttf", "ttc"])
if uploaded_font:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name

# 倒计时音效 (可选)
tick_file = st.sidebar.file_uploader("上传倒计时音效 (可选)", type=["mp3", "wav"])

st.divider()

# ================== 内容输入 ==================
col1, col2 = st.columns(2)
with col1:
    word = st.text_input("单词", value="ambiguous")
    ipa = st.text_input("音标", value="/æmˈbɪɡjuəs/")
    meaning = st.text_input("中文释义", value="adj. 模棱两可的；含糊不清的")
with col2:
    sentence = st.text_area("英文例句", value="His role has always been ambiguous.")
    translation = st.text_input("例句翻译", value="他的角色一直模棱两可。")

# ================== 核心绘图函数 (Pillow) ==================

def draw_app_interface(data, font_path, mode="countdown", countdown_num=3):
    """
    绘制每一帧的图片
    mode: "countdown" (倒计时阶段) / "result" (结果揭示阶段)
    """
    W, H = 1080, 1920
    img = Image.new('RGB', (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    # 1. 绘制顶部 APP 模拟栏 (装饰用)
    draw.rectangle([(0, 0), (W, 150)], fill=COLOR_ACCENT) # 顶部绿条
    
    # 加载字体
    try:
        font_huge = ImageFont.truetype(font_path, 130) # 单词
        font_big = ImageFont.truetype(font_path, 80)   # 倒计时大字
        font_mid = ImageFont.truetype(font_path, 60)   # 音标/释义
        font_small = ImageFont.truetype(font_path, 50) # 例句
        font_giant = ImageFont.truetype(font_path, 600) # 背景大数字
    except:
        font_huge = ImageFont.load_default()
        # ... 降级处理略
    
    # 2. 绘制白色卡片区域 (中间)
    card_margin = 60
    card_top = 250
    card_bottom = 1400
    draw.rectangle([(card_margin, card_top), (W-card_margin, card_bottom)], fill=COLOR_CARD, outline=None)
    
    # ---------------- 核心内容绘制 ----------------
    
    # A. 单词 (始终显示)
    # 居中计算
    w_bbox = draw.textbbox((0, 0), data['word'], font=font_huge)
    w_width = w_bbox[2] - w_bbox[0]
    draw.text(((W - w_width)/2, card_top + 150), data['word'], font=font_huge, fill=COLOR_TEXT_MAIN)
    
    # B. 音标 (始终显示)
    i_bbox = draw.textbbox((0, 0), data['ipa'], font=font_mid)
    i_width = i_bbox[2] - i_bbox[0]
    draw.text(((W - i_width)/2, card_top + 320), data['ipa'], font=font_mid, fill=COLOR_TEXT_SUB)

    # C. 模式分支
    if mode == "countdown":
        # === 倒计时模式 ===
        # 1. 背景大数字 (03, 02, 01)
        num_str = f"0{countdown_num}"
        n_bbox = draw.textbbox((0, 0), num_str, font=font_giant)
        n_w = n_bbox[2] - n_bbox[0]
        n_h = n_bbox[3] - n_bbox[1]
        # 画在卡片中心偏下，颜色很淡
        draw.text(((W - n_w)/2, card_top + 500), num_str, font=font_giant, fill=COLOR_COUNTDOWN)
        
        # 2. 底部提示语
        tip_text = "三秒之后看答案"
        t_bbox = draw.textbbox((0, 0), tip_text, font=font_mid)
        draw.text(((W - (t_bbox[2]-t_bbox[0]))/2, card_bottom - 200), tip_text, font=font_mid, fill=COLOR_ACCENT)

    elif mode == "result":
        # === 结果模式 ===
        content_start_y = card_top + 500
        
        # 1. 中文释义 (加粗/显眼)
        # 简单处理换行
        meaning_text = data['meaning']
        draw.text((card_margin + 80, content_start_y), meaning_text, font=font_mid, fill=COLOR_TEXT_MAIN)
        
        # 2. 分割线
        line_y = content_start_y + 120
        draw.line([(card_margin + 50, line_y), (W - card_margin - 50, line_y)], fill=(240,240,240), width=3)
        
        # 3. 例句
        ex_y = line_y + 80
        draw.text((card_margin + 80, ex_y), "例句:", font=font_small, fill=COLOR_ACCENT)
        
        # 简单的自动换行逻辑 (每行大概25个字，这里粗略估算)
        chars_per_line = 30
        sentence = data['sentence']
        lines = [sentence[i:i+chars_per_line] for i in range(0, len(sentence), chars_per_line)]
        
        current_y = ex_y + 80
        for line in lines:
            draw.text((card_margin + 80, current_y), line, font=font_small, fill=COLOR_TEXT_MAIN)
            current_y += 70
            
        # 4. 翻译
        current_y += 30
        draw.text((card_margin + 80, current_y), data['translation'], font=font_small, fill=COLOR_TEXT_SUB)

    # 3. 底部按钮 (模拟)
    btn_y = 1550
    btn_h = 180
    btn_w = 500
    # 左按钮 (提示一下)
    draw.rounded_rectangle([(100, btn_y), (100+400, btn_y+btn_h)], radius=30, fill=(255,235,238))
    draw.text((100+120, btn_y+60), "提示一下", font=font_mid, fill=(255,100,100))
    
    # 右按钮 (我认识) - 绿色实心
    draw.rounded_rectangle([(W-100-400, btn_y), (W-100, btn_y+btn_h)], radius=30, fill=COLOR_ACCENT)
    draw.text((W-100-280, btn_y+60), "我认识", font=font_mid, fill='white')

    # 保存为临时文件
    temp_path = tempfile.mktemp(suffix=".png")
    img.save(temp_path)
    return temp_path

# ================== 核心处理逻辑 ==================

def generate_tts(text, lang, filename):
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(filename)
    except Exception as e:
        raise Exception(f"语音生成失败: {e}")

def process_video(font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word = os.path.join(temp_dir, "word.mp3")
    audio_sentence = os.path.join(temp_dir, "sentence.mp3")
    output_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音
    try:
        generate_tts(data['word'], 'en', audio_word)
        # 结果页语音：读单词 + 读例句
        full_text = f"{data['sentence']}"
        generate_tts(full_text, 'en', audio_sentence)
    except Exception as e:
        st.error(str(e))
        return None

    # 加载单词音频
    clip_word_audio = AudioFileClip(audio_word)
    
    # 加载倒计时音效
    clip_tick_audio = None
    if tick_path:
        clip_tick_audio = AudioFileClip(tick_path).subclip(0, 1) # 截取1秒

    # === 制作第一部分：3秒倒计时 (3, 2, 1) ===
    countdown_clips = []
    
    for i in [3, 2, 1]:
        # A. 生成这一秒的画面 (显示数字 i)
        img_path = draw_app_interface(data, font_path, mode="countdown", countdown_num=i)
        clip_img = ImageClip(img_path).set_duration(1.0) # 每一张图显示1秒
        
        # B. 这一秒的音频：单词发音 + 滴答声 (混合)
        # 确保音频不超过1秒
        current_audio = clip_word_audio
        if clip_tick_audio:
            current_audio = CompositeAudioClip([clip_word_audio, clip_tick_audio])
            
        # 强制音频限时1秒 (防止单词太长导致画面不同步)
        if current_audio.duration > 1:
            current_audio = current_audio.subclip(0, 1)
            
        clip_img = clip_img.set_audio(current_audio)
        countdown_clips.append(clip_img)
    
    # 合并倒计时片段 (3秒)
    intro_clip = concatenate_videoclips(countdown_clips)

    # === 制作第二部分：结果展示 ===
    # 结果页画面
    res_img_path = draw_app_interface(data, font_path, mode="result")
    
    # 结果页音频 (例句)
    clip_sentence_audio = AudioFileClip(audio_sentence)
    
    # 画面时长 = 音频时长 + 1秒缓冲
    duration = clip_sentence_audio.duration + 1.5
    result_clip = ImageClip(res_img_path).set_duration(duration)
    result_clip = result_clip.set_audio(clip_sentence_audio)

    # === 最终合并 ===
    final_video = concatenate_videoclips([intro_clip, result_clip])
    final_video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
    
    return output_path

# ================== 执行按钮 ==================
if st.button("🚀 生成仿APP视频", type="primary"):
    if not current_font_path:
        st.error("❌ 必须上传字体文件才能生成界面！")
    else:
        with st.spinner("正在绘制APP界面..."):
            try:
                # 处理音效
                t_tick = None
                if tick_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        f.write(tick_file.read())
                        t_tick = f.name
                
                data = {"word": word, "ipa": ipa, "meaning": meaning, "sentence": sentence, "translation": translation}
                
                video_path = process_video(current_font_path, t_tick, data)
                
                if video_path:
                    st.success("✅ 视频已生成！")
                    st.video(video_path)
            except Exception as e:
                st.error(f"出错: {e}")
