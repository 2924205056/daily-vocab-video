import streamlit as st
import asyncio
import edge_tts
from moviepy.editor import *
import tempfile
import os

# 页面基础设置
st.set_page_config(page_title="单词视频生成器", layout="wide")
st.title("🎬 每日单词视频生成器")
st.markdown("上传素材 -> 输入单词 -> 生成视频。")

# ================== 侧边栏：素材配置 ==================
st.sidebar.header("1. 上传必要素材")
st.sidebar.info("💡 云端服务器没有中文字体，请务必上传字体文件！")

# 1. 上传背景图
bg_file = st.sidebar.file_uploader("上传背景图 (9:16竖屏)", type=["jpg", "png", "jpeg"])
# 2. 上传字体
font_file = st.sidebar.file_uploader("上传字体文件 (.ttf/.ttc)", type=["ttf", "ttc"])
# 3. 上传音效
tick_file = st.sidebar.file_uploader("上传倒计时音效 (.mp3, 可选)", type=["mp3", "wav"])

# ================== 主界面：内容输入 ==================
st.header("2. 输入单词信息")
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
    # 创建临时文件夹
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音
    # 单词部分 (英文男声)
    asyncio.run(generate_tts(data['word'], "en-US-ChristopherNeural", audio_word_path))
    
    # 完整部分 (为了中文自然，这里使用中文语音包读全文，你可以根据喜好调整)
    full_text = f"{data['word']}... {data['meaning']}... {data['sentence']}"
    asyncio.run(generate_tts(full_text, "zh-CN-YunxiNeural", audio_full_path))

    # 2. 载入素材
    # 背景
    if bg_path:
        bg_clip = ImageClip(bg_path).resize((1080, 1920))
    else:
        bg_clip = ColorClip(size=(1080, 1920), color=(0,0,0)) # 默认黑底

    # 字体 (如果用户没传，尝试用 Arial，但在 Linux 上中文可能会乱码)
    used_font = font_path if font_path else "Arial"

    # 音频
    audio_word_clip = AudioFileClip(audio_word_path)
    audio_full_clip = AudioFileClip(audio_full_path)
    
    tick_sfx = None
    if tick_path:
        try:
            tick_sfx = AudioFileClip(tick_path).subclip(0, 3).volumex(0.3)
        except:
            pass

    # --- 阶段 1: 提问 (3秒+单词时长) ---
    phase1_duration = max(3.5, audio_word_clip.duration + 2.5)
    
    # 制作文字图片
    txt_word_huge = TextClip(data['word'], fontsize=150, color='white', font=used_font, method='label')
    txt_word_huge = txt_word_huge.set_position('center').set_duration(phase1_duration)
    
    # 混合音频
    audio_track_1 = audio_word_clip
    if tick_sfx:
        # 单词读完或0.5秒后开始倒计时
        audio_track_1 = CompositeAudioClip([audio_word_clip, tick_sfx.set_start(0.5)])
    
    clip_phase_1 = CompositeVideoClip([bg_clip.set_duration(phase1_duration), txt_word_huge])
    clip_phase_1 = clip_phase_1.set_audio(audio_track_1.set_duration(phase1_duration))

    # --- 阶段 2: 揭示 (释义时长) ---
    phase2_duration = audio_full_clip.duration + 1.0
    
    txt_word_top = TextClip(data['word'] + "\n" + data['ipa'], fontsize=100, color='yellow', font=used_font, method='label')
    txt_word_top = txt_word_top.set_position(('center', 400)).set_duration(phase2_duration)
    
    txt_meaning = TextClip(data['meaning'], fontsize=70, color='white', font=used_font, method='caption', size=(900, None))
    txt_meaning = txt_meaning.set_position(('center', 'center')).set_duration(phase2_duration)
    
    ex_text = f"{data['sentence']}\n{data['translation']}"
    txt_example = TextClip(ex_text, fontsize=50, color='lightgrey', font=used_font, method='caption', size=(900, None))
    txt_example = txt_example.set_position(('center', 1300)).set_duration(phase2_duration)

    clip_phase_2 = CompositeVideoClip([
        bg_clip.set_duration(phase2_duration),
        txt_word_top,
        txt_meaning,
        txt_example
    ])
    clip_phase_2 = clip_phase_2.set_audio(audio_full_clip)

    # --- 合成最终视频 ---
    final_video = concatenate_videoclips([clip_phase_1, clip_phase_2])
    final_video.write_videofile(output_video_path, fps=24, codec='libx264', audio_codec='aac')
    
    return output_video_path

# ================== 执行按钮 ==================
st.divider()
if st.button("🚀 生成视频", type="primary"):
    if not font_file:
        st.error("❌ 错误：请在左侧侧边栏上传字体文件（.ttf 或 .ttc），否则无法生成文字。")
    else:
        with st.spinner("正在合成视频... 请耐心等待 15-30 秒..."):
            try:
                # 处理上传的临时文件
                t_bg = None
                if bg_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                        f.write(bg_file.read())
                        t_bg = f.name
                
                t_font = None
                if font_file:
                    suffix = ".ttc" if font_file.name.endswith(".ttc") else ".ttf"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                        f.write(font_file.read())
                        t_font = f.name
                
                t_tick = None
                if tick_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        f.write(tick_file.read())
                        t_tick = f.name

                data = {
                    "word": word, "ipa": ipa, "meaning": meaning, 
                    "sentence": sentence, "translation": translation
                }
                
                video_path = process_video(t_bg, t_font, t_tick, data)
                
                st.success("✅ 视频制作完成！")
                st.video(video_path)
                
                with open(video_path, "rb") as file:
                    st.download_button(
                        label="⬇️ 下载视频",
                        data=file,
                        file_name=f"{word}_vocab.mp4",
                        mime="video/mp4"
                    )
            except Exception as e:
                st.error(f"发生错误: {e}")
