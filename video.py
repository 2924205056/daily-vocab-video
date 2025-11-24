import streamlit as st
import asyncio
import edge_tts
from moviepy.editor import *
import tempfile
import os

# ================= 配置区域 =================
# 这里的字体文件名必须和你上传到 GitHub (或本地文件夹) 的名字完全一致
DEFAULT_FONT = "font.ttf" 

# 更稳定的语音角色配置
VOICE_EN = "en-US-AriaNeural"      # 微软最稳的英文女声
VOICE_ZH = "zh-CN-XiaoxiaoNeural"  # 微软最稳的中文女声

# ================= 页面设置 =================
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器 (修复版)")

# ================== 侧边栏：素材配置 ==================
st.sidebar.header("⚙️ 素材配置")

# 检查字体是否存在
if not os.path.exists(DEFAULT_FONT):
    st.sidebar.error(f"⚠️ 警告：未找到 {DEFAULT_FONT}！请确保字体文件已上传且重命名正确。")
    current_font = "Arial" 
else:
    st.sidebar.success(f"✅ 已加载字体: {DEFAULT_FONT}")
    current_font = DEFAULT_FONT

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

# ================== 核心逻辑函数 (修复版) ==================

async def generate_tts_safe(text, voice, output_file):
    """
    带重试机制的语音生成函数
    """
    if not text or len(text.strip()) == 0:
        return # 文本为空不处理
        
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
    except Exception as e:
        # 如果首选声音失败，尝试备用声音 (Guy 是男声，Yunxi 是男声)
        print(f"首选语音失败: {e}，尝试备用语音...")
        try:
            backup_voice = "en-US-GuyNeural" if "en-US" in voice else "zh-CN-YunxiNeural"
            communicate = edge_tts.Communicate(text, backup_voice)
            await communicate.save(output_file)
        except Exception as e2:
            raise Exception(f"语音生成彻底失败，请检查网络连接。错误信息: {str(e2)}")

def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音 (使用修复版函数)
    try:
        asyncio.run(generate_tts_safe(data['word'], VOICE_EN, audio_word_path))
        
        full_text = f"{data['word']}... {data['meaning']}... {data['sentence']}"
        asyncio.run(generate_tts_safe(full_text, VOICE_ZH, audio_full_path))
    except Exception as e:
        st.error(f"❌ 语音生成失败：{e}")
        return None

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
    # 确保时长至少为3秒，如果语音更长则跟随语音
    phase1_duration = max(3.5, audio_word_clip.duration + 2.5)
    
    txt_word_huge = TextClip(data['word'], fontsize=150, color='white', font=font_path, method='label')
    txt_word_huge = txt_word_huge.set_position('center').set_duration(phase1_duration)
    
    audio_track_1 = audio_word_clip
    if tick_sfx:
        # 单词读完或0.5秒后开始倒计时
        audio_track_1 = CompositeAudioClip([audio_word_clip, tick_sfx.set_start(0.5)])
    
    clip_phase_1 = CompositeVideoClip([bg_clip.set_duration(phase1_duration), txt_word_huge])
    clip_phase_1 = clip_phase_1.set_audio(audio_track_1.set_duration(phase1_duration))

    # --- 阶段 2 ---
    phase2_duration = audio_full_clip.duration + 1.0
    
    txt_word_top = TextClip(data['word'] + "\n" + data['ipa'], fontsize=100, color='yellow', font=font
