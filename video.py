import streamlit as st
import asyncio
import edge_tts
from moviepy.editor import *
import tempfile
import os

# ================= 配置区域 =================
# 这里填你上传到 GitHub 的字体文件名
# 如果你传的是 font.ttf 就填 "font.ttf"
# 如果你传的是 msyh.ttc 就填 "msyh.ttc"
DEFAULT_FONT = "font.ttf" 

# ================= 页面设置 =================
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器 (自动加载字体版)")

# ================== 侧边栏：素材配置 ==================
st.sidebar.header("⚙️ 素材配置")

# 检查字体是否存在
if not os.path.exists(DEFAULT_FONT):
    st.sidebar.error(f"⚠️ 警告：未在仓库中找到 {DEFAULT_FONT}！请去 GitHub 上传字体文件。")
    current_font = "Arial" # 降级处理
else:
    st.sidebar.success(f"✅ 已自动加载字体: {DEFAULT_FONT}")
    current_font = DEFAULT_FONT

# 背景图还是建议保留上传功能，因为每天可能想换不一样的图
# 但如果你想固定一张图，也可以像字体一样处理
bg_file = st.sidebar.file_uploader("上传背景图 (9:16竖屏, 不传则用黑底)", type=["jpg", "png", "jpeg"])
tick_file = st.sidebar.file_uploader("上传倒计时音效 (可选)", type=["mp3", "wav"])

# ================== 主界面：内容输入 ==================
st.divider()
col1, col2 = st.columns(2)

with col1:
    word = st.text_input("单词 (Word)", value="Ambition")
    ipa = st.text_input("音标 (IPA)", value="/æmˈbɪʃn/")
    meaning = st.text_input("中文释义", value="n. 野心；雄心；抱负")

with col2:
    sentence = st.text_area("英文例句", value="Her ambition was to become a pilot.")
    translation = st.text_input("例句翻译", value="她的抱负是成为一名飞行员。")

# ================== 核心逻辑函数 ==================

async def generate_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音
    asyncio.run(generate_tts(data['word'], "en-US-ChristopherNeural", audio_word_path))
    full_text = f"{data['word']}... {data['meaning']}... {data['sentence']}"
    asyncio.run(generate_tts(full_text, "zh-CN-YunxiNeural", audio_full_path))

    # 2. 载入素材
    if bg_path:
        bg_clip = ImageClip(bg_path).resize((1080, 1920))
    else:
        bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0))

    audio_word_clip = AudioFileClip(audio_word_path)
    audio_full_clip = AudioFileClip(audio_full_path)
    
    tick_sfx = None
    if tick_path:
        try:
            tick_sfx = AudioFileClip(tick_path).subclip(0, 3).volumex(0.3)
        except:
            pass

    # --- 阶段 1 ---
    phase1_duration = max(3.5, audio_word_clip.duration + 2.5)
    
    txt_word_huge = TextClip(data['word'], fontsize=150, color='white', font=font_path, method='label')
    txt_word_huge = txt_word_huge.set_position('center').set_duration(phase1_duration)
    
    audio_track_1 = audio_word_clip
    if tick_sfx:
        audio_track_1 = CompositeAudioClip([audio_word_clip, tick_sfx.set_start(0.5)])
    
    clip_phase_1 = CompositeVideoClip([bg_clip.set_duration(phase1_duration), txt_word_huge])
    clip_phase_1 = clip_phase_1.set_audio(audio_track_1.set_duration(phase1_duration))

    # --- 阶段 2 ---
    phase2_duration = audio_full_clip.duration + 1.0
    
    txt_word_top = TextClip(data['word'] + "\n" + data['ipa'], fontsize=100, color='yellow', font=font_path, method='label')
    txt_word_top = txt_word_top.set_position(('center', 400)).set_duration(phase2_duration)
    
    txt_meaning = TextClip(data['meaning'], fontsize=70, color='white', font=font_path, method='caption', size=(900, None))
    txt_meaning = txt_meaning.set_position(('center', 'center')).set_duration(phase2_duration)
    
    ex_text = f"{data['sentence']}\n{data['translation']}"
    txt_example = TextClip(ex_text, fontsize=50, color='lightgrey', font=font_path, method='caption', size=(900, None))
    txt_example = txt_example.set_position(('center', 1300)).set_duration(phase2_duration)

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
if st.button("🚀 生成视频", type="primary"):
    with st.spinner("正在合成..."):
        try:
            # 处理背景图
            t_bg = None
            if bg_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                    f.write(bg_file.read())
                    t_bg = f.name
            
            # 处理音效
            t_tick = None
            if tick_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    f.write(tick_file.read())
                    t_tick = f.name

            data = {"word": word, "ipa": ipa, "meaning": meaning, "sentence": sentence, "translation": translation}
            
            # 直接传入 current_font (这是文件路径字符串)
            video_path = process_video(t_bg, current_font, t_tick, data)
            
            st.success("✅ 完成！")
            st.video(video_path)
            with open(video_path, "rb") as file:
                st.download_button("⬇️ 下载视频", data=file, file_name=f"{word}_video.mp4", mime="video/mp4")
                
        except Exception as e:
            st.error(f"出错: {e}")
