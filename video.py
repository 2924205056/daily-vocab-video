import streamlit as st
import asyncio
import edge_tts
from moviepy.editor import *
import tempfile
import os
import platform

# ================= 配置区域 =================
DEFAULT_FONT = "font.ttf" 

# 微软语音配置 (云端运行时用)
VOICE_EN = "en-US-ChristopherNeural"
VOICE_ZH = "zh-CN-XiaoxiaoNeural"

# ================= 页面设置 =================
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器 (Mac本地 + 云端双模版)")

# ================== 侧边栏 ==================
st.sidebar.header("⚙️ 素材配置")
if not os.path.exists(DEFAULT_FONT):
    st.sidebar.error(f"⚠️ 警告：未找到 {DEFAULT_FONT}！")
    current_font = "Arial" 
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

# ================== 核心语音函数 (关键修改) ==================

def use_mac_tts(text, lang, filename):
    """
    使用 Mac 自带的 'say' 命令生成语音，不需要联网
    """
    # 英文用 Samantha (Siri声线), 中文用 Ting-Ting
    voice = "Samantha" if lang == "en" else "Ting-Ting"
    
    # Mac 的 say 命令生成的是 aiff 格式，ffmpeg (moviepy) 可以直接读取
    # 这里的 -o filename 是输出路径
    cmd = f'say -v {voice} -o "{filename}" "{text}"'
    print(f"正在使用 Mac 本地语音: {cmd}")
    os.system(cmd)

async def generate_tts_smart(text, voice, output_file, lang_code="en"):
    """
    智能语音生成：优先尝试微软 Edge-TTS，失败则切换 Mac 本地
    """
    if not text: return

    # 1. 尝试微软 Edge-TTS (网络好时音质最好)
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
    except Exception as e:
        print(f"微软语音连接失败 ({e})，切换 Mac 本地语音...")
        
        # 2. 如果失败，检查是不是在 Mac 上，是的话用本地语音
        if platform.system() == 'Darwin':
            # 删除可能存在的空文件
            if os.path.exists(output_file): os.remove(output_file)
            # 调用 Mac 系统语音
            use_mac_tts(text, lang_code, output_file)
        else:
            st.error("❌ 语音生成失败：网络不通且非 Mac 系统。请部署到云端使用。")
            raise e

def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.aiff") # Mac say 默认格式兼容性更好
    audio_full_path = os.path.join(temp_dir, "full.aiff")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音 (智能模式)
    try:
        # 单词 (英文)
        asyncio.run(generate_tts_smart(data['word'], VOICE_EN, audio_word_path, "en"))
        
        # 句子 (中文+英文)
        full_text = f"{data['word']}... {data['meaning']}... {data['sentence']}"
        asyncio.run(generate_tts_smart(full_text, VOICE_ZH, audio_full_path, "zh"))
    except:
        return None

    # 2. 载入素材
    if bg_path:
        bg_clip = ImageClip(bg_path).resize((1080, 1920))
    else:
        bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0))

    # 读取音频 (MoviePy 会自动处理 aiff/mp3)
    try:
        audio_word_clip = AudioFileClip(audio_word_path)
        audio_full_clip = AudioFileClip(audio_full_path)
    except OSError:
        st.error("❌ 音频文件生成失败，可能是 Mac 没有安装中文语音包 (系统偏好设置->辅助功能->朗读内容->系统声音 选婷婷)")
        return None
    
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
if st.button("🚀 生成视频 (Mac兼容版)", type="primary"):
    with st.spinner("正在合成... (如联网失败会自动切换Mac语音)"):
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
                st.success("✅ 完成！")
                st.video(video_path)
        except Exception as e:
            st
