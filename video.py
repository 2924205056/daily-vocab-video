def process_video(bg_path, font_path, tick_path, data):
    temp_dir = tempfile.mkdtemp()
    audio_word_path = os.path.join(temp_dir, "word.mp3")
    audio_full_path = os.path.join(temp_dir, "full.mp3")
    output_video_path = os.path.join(temp_dir, "output.mp4")

    # 1. 生成语音
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
    
    # === 这里就是你报错的地方，已修复 ===
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
