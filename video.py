import streamlit as st
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile
import os

# ================= 配置区域 =================
# 这里的名字必须和你上传到 GitHub 的字体文件名一致
# 建议去 GitHub 仓库里把你的字体文件重命名为 font.ttf
DEFAULT_FONT_NAME = "font.ttf" 

# ================= 页面设置 =================
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器 (终极稳定版)")
st.markdown("""
**版本特性：**
1. ✅ 使用 Google 语音 (gTTS)，解决 IP 被封问题。
2. ✅ 使用 Pillow 原生绘图，解决 ImageMagick 安全策略报错。
3. ✅ 修复音频时长错误，自动适配倒计时。
""")

# ================== 侧边栏：素材配置 ==================
st.sidebar.header("⚙️ 素材配置")

# 1. 字体逻辑：优先用 GitHub 里的，如果没有，允许用户临时上传
current_font_path = None

if os.path.exists(DEFAULT_FONT_NAME):
    st.sidebar.success(f"✅ 已加载仓库字体: {DEFAULT_FONT_NAME}")
    current_font_path = DEFAULT_FONT_NAME
else:
    st.sidebar.warning(f"⚠️ 仓库中未找到 {DEFAULT_FONT_NAME}，请上传字体！")

# 允许临时上传字体覆盖
uploaded_font = st.sidebar.file_uploader("临时替换字体 (可选)", type=["ttf", "ttc"])
if uploaded_font:
    # 保存临时字体
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
        tmp_font.write(uploaded_font.read())
        current_font_path = tmp_font.name
        st.sidebar.success("✅ 已使用临时上传的字体")

# 2. 其他素材
bg_file = st.sidebar.file_uploader("上传背景图 (9:16竖屏)", type=["jpg", "png", "jpeg"])
tick_file = st.sidebar.file_uploader("上传倒计时音效 (可选)", type=["mp3", "wav"])

st.divider()

# ================== 主界面：内容输入 ==================
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
    """生成谷歌语音"""
    if not text: return
    try:
        # lang: 'en' for English, 'zh-CN' for Chinese
        tts = gTTS(text=text, lang=lang)
        tts.save(output_file)
    except Exception as e:
        raise Exception(f"Google语音生成失败: {e}")

def create_text_clip_pil(text, font_path, font_size, color, duration, width=1080, height=1920, position="center", y_offset=0):
    """
    使用 Pillow 绘制文字图片，转为 MoviePy ImageClip
    彻底绕过 ImageMagick
    """
    # 1. 创建透明画布
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 2. 加载字体
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
        print("字体加载失败，使用默认字体")

    # 3. 计算文字大小和位置
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # 默认居中
    x = (width - text_w) / 2
    y = (height - text_h) / 2
    
    # 如果指定了 y_offset (垂直偏移)，则调整 y
    # y_offset 比如 200 代表靠上，1300 代表靠下
    if y_offset != 0:
        y = y_offset

    # 4. 颜色映射
    color_map = {
        'white': (255, 255, 255),
        'yellow': (255, 215, 0),
        'lightgrey': (211, 211, 211),
        'black': (0, 0, 0)
    }
    rgb = color_map.get(color, (255, 255, 255))
    
    # 5. 绘制
    draw.text((x, y), text, font=font, fill=rgb)
    
    # 6. 保存临时文件并生成 Clip
    temp_img_path = tempfile.mktemp(suffix=".png")
    img.save(temp_img_path)
    
    # 创建 Clip
    clip = ImageClip(temp_img_path).set_duration(duration)
    return clip

def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # --- 1. 生成语音 (gTTS) ---
    try:
        # 单词 (英文)
        generate_google_tts(data['word'], 'en', audio_word_path)
        # 全文 (用中文引擎读混合文本)
        full_text = f"{data['word']}，{data['meaning']}，{data['sentence']}"
        generate_google_tts(full_text, 'zh-CN', audio_full_path)
    except Exception as e:
        st.error(f"❌ 语音生成失败: {e}")
        return None

    # --- 2. 处理背景图 ---
    if bg_path:
        try:
            # 用 Pillow 调整大小，避免调用 ImageMagick
            pil_bg = Image.open(bg_path).resize((1080, 1920))
            bg_temp = os.path.join(temp_dir, "bg_resized.jpg")
            pil_bg.save(bg_temp)
            bg_clip = ImageClip(bg_temp)
        except Exception as e:
            st.warning(f"背景图处理出错: {e}，将使用黑底。")
            bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0))
    else:
        bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0))

    # --- 3. 读取音频 ---
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

    # ================= 制作阶段 1 (提问) =================
    # 时长逻辑：至少3.5秒，如果单词读得慢，就延长
    phase1_duration = max(3.5, audio_word_clip.duration + 2.5)
    
    # 绘制巨大的单词 (居中)
    txt_word_huge = create_text_clip_pil(
        data['word'], font_path, 150, 'white', phase1_duration
    )
    
    # 组合音频：单词声 + 倒计时
    if tick_sfx:
        # set_start(0.5) 让倒计时稍微晚一点进
        audio_track_1 = CompositeAudioClip([audio_word_clip, tick_sfx.set_start(0.5)])
    else:
        audio_track_1 = audio_word_clip
    
    # 合成阶段1
    # 注意：这里我们只给 bg_clip 设置时长，不强制拉伸 audio
    clip_phase_1 = CompositeVideoClip([bg_clip.set_duration(phase1_duration), txt_word_huge])
    clip_phase_1 = clip_phase_1.set_audio(audio_track_1)

    # ================= 制作阶段 2 (揭示) =================
    phase2_duration = audio_full_clip.duration + 1.0
    
    # 绘制上方单词+音标 (y_offset=200)
    txt_word_top = create_text_clip_pil(
        data['word'] + "\n" + data['ipa'], font_path, 100, 'yellow', phase2_duration, y_offset=200
    )
    
    # 绘制中间释义 (居中)
    txt_meaning = create_text_clip_pil(
        data['meaning'], font_path, 70, 'white', phase2_duration
    )
    
    # 绘制下方例句 (y_offset=1300)
    ex_text = f"{data['sentence']}\n{data['translation']}"
    txt_example = create_text_clip_pil(
        ex_text, font_path, 50, 'lightgrey', phase2_duration, y_offset=1300
    )

    clip_phase_2 = CompositeVideoClip([
        bg_clip.set_duration(phase2_duration),
        txt_word_top,
        txt_meaning,
        txt_example
    ])
    clip_phase_2 = clip_phase_2.set_audio(audio_full_clip)

    # ================= 最终合并 =================
    final_video = concatenate_videoclips([clip_phase_1, clip_phase_2])
    final_video.write_videofile(output_video_path, fps=24, codec='libx264', audio_codec='aac')
    
    return output_video_path

# ================== 执行按钮 ==================
if st.button("🚀 生成视频 (最终版)", type="primary"):
    if not current_font_path:
        st.error("❌ 无法生成：缺少字体！请在侧边栏上传字体，或确保 GitHub 仓库里有 font.ttf")
    else:
        with st.spinner("正在合成视频... (约15-20秒)"):
            try:
                # 处理上传的临时文件
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

                data = {
                    "word": word, "ipa": ipa, "meaning": meaning, 
                    "sentence": sentence, "translation": translation
                }
                
                video_path = process_video(t_bg, current_font_path, t_tick, data)
                
                if video_path:
                    st.balloons()
                    st.success("✅ 视频制作成功！")
                    st.video(video_path)
                    
                    with open(video_path, "rb") as file:
                        st.download_button(
                            label="⬇️ 下载视频",
                            data=file,
                            file_name=f"{word}_vocab.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"发生未知错误: {e}")
