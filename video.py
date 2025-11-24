import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import os

# ================= 配置区域 =================
DEFAULT_FONT = "font.ttf" 

# ================= 页面设置 =================
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器 (Pillow绘图版)")
st.markdown("✅ 已移除 ImageMagick 依赖，使用 Pillow 原生绘图，解决 Security Policy 报错。")

# ================== 侧边栏 ==================
st.sidebar.header("⚙️ 素材配置")

if not os.path.exists(DEFAULT_FONT):
    st.sidebar.error(f"⚠️ 未找到 {DEFAULT_FONT}！请上传字体文件。")
    current_font = None # Pillow 需要确切路径，没有则报错
else:
    st.sidebar.success(f"✅ 已加载字体: {DEFAULT_FONT}")
    current_font = DEFAULT_FONT

bg_file = st.sidebar.file_uploader("上传背景图", type=["jpg", "png", "jpeg"])
tick_file = st.sidebar.file_uploader("上传倒计时音效", type=["mp3", "wav"])

st.divider()
col1, col2 = st.columns(2)
with col1:
    word = st.text_input("单词", value="Ambition")
    ipa = st.text_input("音标", value="/æmˈbɪʃn/")
    meaning = st.text_input("中文释义", value="n. 野心；雄心；抱负")
with col2:
    sentence = st.text_area("英文例句", value="Her ambition was to become a pilot.")
    translation = st.text_input("例句翻译", value="她的抱负是成为一名飞行员。")

# ================== 核心功能函数 ==================

def generate_google_tts(text, lang, output_file):
    if not text: return
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(output_file)
    except Exception as e:
        raise Exception(f"Google语音生成失败: {e}")

# 🔥【核心修改】用 Pillow 替代 MoviePy 生成文字图片
def create_text_clip_pil(text, font_path, font_size, color, duration, width=1080, height=None, position="center"):
    """
    使用 Pillow 手动绘制文字，然后转为 MoviePy 的 ImageClip
    """
    # 1. 创建透明画布
    # 如果 height 为 None，说明是局部文字，我们先估算一个高度
    canvas_w = width
    canvas_h = 1920 if height is None else height 
    
    img = Image.new('RGBA', (canvas_w, canvas_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 2. 加载字体
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        # 如果加载失败，使用默认字体（虽然丑但不会崩）
        font = ImageFont.load_default()
    
    # 3. 计算文字位置使其居中
    # 使用 textbbox 获取文字宽高
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    if position == "center":
        x = (canvas_w - text_w) / 2
        y = (canvas_h - text_h) / 2
    else:
        # 这里简化处理，如果是指定位置，我们还是先画在画布中心，
        # 然后靠 MoviePy 的 set_position 去定位 Clip
        x = (canvas_w - text_w) / 2
        y = (canvas_h - text_h) / 2

    # 4. 绘制文字
    # 将颜色名称转换为 RGB，简单处理几种颜色
    color_map = {'white': (255, 255, 255), 'yellow': (255, 215, 0), 'lightgrey': (211, 211, 211)}
    rgb = color_map.get(color, (255, 255, 255))
    
    draw.text((x, y), text, font=font, fill=rgb)
    
    # 5. 转为 MoviePy ImageClip
    # 保存为临时文件再读取是兼容性最好的方法
    temp_img_path = tempfile.mktemp(suffix=".png")
    img.save(temp_img_path)
    
    clip = ImageClip(temp_img_path).set_duration(duration)
    
    # 如果是全屏画布模式，就不需要再设置位置了；如果是小组件模式，可能需要
    if height is not None:
        # 如果指定了画布高度（比如全屏），通常意味着文字已经画在图上了
        return clip
    else:
        return clip

def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音
    try:
        generate_google_tts(data['word'], 'en', audio_word_path)
        full_text = f"{data['word']}，{data['meaning']}，{data['sentence']}"
        generate_google_tts(full_text, 'zh-CN', audio_full_path)
    except Exception as e:
        st.error(f"❌ 语音生成失败: {e}")
        return None

    # 2. 载入素材
    if bg_path:
        # 注意：这里如果报错，可能是 ImageMagick resize 问题
        # 我们改用 PIL resize 避免 ImageMagick
        pil_bg = Image.open(bg_path).resize((1080, 1920))
        pil_bg.save(os.path.join(temp_dir, "resized_bg.jpg"))
        bg_clip = ImageClip(os.path.join(temp_dir, "resized_bg.jpg"))
    else:
        bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0))

    try:
        audio_word_clip = AudioFileClip(audio_word_path)
        audio_full_clip = AudioFileClip(audio_full_path)
    except Exception as e:
        st.error(f"❌ 音频读取失败: {e}")
        return None
    
    tick_sfx = None
    if tick_path:
        try:
            tick_sfx = AudioFileClip(tick_path).subclip(0, 3).volumex(0.3)
        except:
            pass

    # --- 阶段 1 ---
    phase1_duration = max(3.5, audio_word_clip.duration + 2.5)
    
    # 🔥 使用新的 PIL 绘图函数代替 TextClip
    # 画布高度设为 1920 代表全屏透明图层，文字居中
    txt_word_huge = create_text_clip_pil(
        data['word'], font_path, 150, 'white', phase1_duration, height=1920, position="center"
    )
    
    audio_track_1 = audio_word_clip
    if tick_sfx:
        audio_track_1 = CompositeAudioClip([audio_word_clip, tick_sfx.set_start(0.5)])
    
    clip_phase_1 = CompositeVideoClip([bg_clip.set_duration(phase1_duration), txt_word_huge])
    clip_phase_1 = clip_phase_1.set_audio(audio_track_1.set_duration(phase1_duration))

    # --- 阶段 2 ---
    phase2_duration = audio_full_clip.duration + 1.0
    
    # 单词+音标 (为了布局方便，我们生成透明图片，然后用 set_position 放置)
    # 这里我们创建小一点的图片，然后让 MoviePy 摆放位置
    txt_word_top = create_text_clip_pil(
        data['word'] + "\n" + data['ipa'], font_path, 100, 'yellow', phase2_duration, height=600
    ).set_position(('center', 200)) # 垂直位置200
    
    txt_meaning = create_text_clip_pil(
        data['meaning'], font_path, 70, 'white', phase2_duration, height=400
    ).set_position('center')
    
    ex_text = f"{data['sentence']}\n{data['translation']}"
    # 稍微处理下换行，Pillow 不会自动换行，这里简单硬切，以后可以优化
    txt_example = create_text_clip_pil(
        ex_text, font_path, 50, 'lightgrey', phase2_duration, height=600
    ).set_position(('center', 1300)) # 垂直位置1300

    clip_phase_2 = CompositeVideoClip([
        bg_clip.set_duration(phase2_duration),
        txt_word_top,
        txt_meaning,
        txt_example
    ])
    clip_phase_2 = clip_phase_2.set_audio(audio_full_clip)

    final_video = concatenate_videoclips([clip_phase_1, clip_phase_2])
    final_video.write_videofile(output_video_path, fps=24, codec='libx264', audio_codec='aac')
    return output_video_path

# ================== 执行 ==================
if st.button("🚀 生成视频 (Pillow版)", type="primary"):
    if not current_font:
        st.error("❌ 无法生成：缺少字体文件。请确保 GitHub 仓库中有 font.ttf")
    else:
        with st.spinner("正在合成 (Pillow绘图模式)..."):
            try:
                t_bg = None
                if bg_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                        f.write(bg_file.read())
                        t_bg = f.name
                
                t_tick = None
                if tick_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        f.write(tick_file.read())
                        t_tick = f.name

                data = {"word": word, "ipa": ipa, "meaning": meaning, "sentence": sentence, "translation": translation}
                
                video_path = process_video(t_bg, current_font, t_tick, data)
                
                if video_path:
                    st.success("✅ 成功！已绕过 ImageMagick 限制。")
                    st.video(video_path)
                    with open(video_path, "rb") as file:
                        st.download_button("⬇️ 下载视频", data=file, file_name=f"{word}_video.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"出错: {e}")
