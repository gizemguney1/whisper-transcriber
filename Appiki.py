import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import shutil
import math


if os.system("ffmpeg -version") != 0:
    st.error("FFmpeg bulunamadı. Lütfen sisteme FFmpeg yükleyin.")
    st.stop()

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("OPENAI_API_KEY eksik.")
    st.stop()

st.title("Transkript Oluşturucu")


def reset_states():
    st.session_state.transcript_text = None
    st.session_state.audio_path = None
    st.session_state.audio_ready = False

if "transcript_text" not in st.session_state:
    reset_states()

# ------------------ FONKSİYONLAR ------------------

def split_audio(input_path, segment_minutes=10):
    """
    Dosyayı ffmpeg ile belirtilen dakika uzunluğunda parçalara böler.
    OpenAI 25MB limiti için genelde 10-15 dk güvenlidir.
    """
    output_dir = tempfile.mkdtemp()

    output_pattern = os.path.join(output_dir, "chunk%03d.mp3")
    
   
    seconds = segment_minutes * 60
    

    cmd = (
        f'ffmpeg -i "{input_path}" -f segment -segment_time {seconds} '
        f'-c:a libmp3lame -b:a 128k "{output_pattern}" -y'
    )
    
    os.system(cmd)
    
  
    files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("chunk")])
    return files, output_dir

def transcribe_large_file(file_path):
    """
    Dosyayı böler, tek tek çevirir ve birleştirir.
    """
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
 
    if file_size_mb < 24:
        with open(file_path, "rb") as audio:
            res = client.audio.transcriptions.create(model="whisper-1", file=audio)
        return res.text
    
    
    st.info(f"Dosya büyük ({file_size_mb:.2f} MB). Parçalanarak işleniyor, lütfen bekleyin...")
    
   
    progress_text = "Dosya parçalanıyor..."
    my_bar = st.progress(0, text=progress_text)
    
    chunks, temp_dir = split_audio(file_path, segment_minutes=10)
    total_chunks = len(chunks)
    
    full_transcript = []
    
    for i, chunk in enumerate(chunks):
        my_bar.progress((i) / total_chunks, text=f"Parça {i+1} / {total_chunks} işleniyor...")
        
        with open(chunk, "rb") as audio:
            res = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio
            )
            full_transcript.append(res.text)
            
    my_bar.progress(1.0, text="Tamamlandı!")
    
    dım
    shutil.rmtree(temp_dir)
    
    return " ".join(full_transcript)


secenek = st.radio("İşlem türü:", ["Dosya yükle", "Link gir"], horizontal=True)

# ---------- DOSYA ----------
if secenek == "Dosya yükle":
    uploaded_file = st.file_uploader("Dosya seç", type=["mp3", "wav", "m4a", "mp4", "mov", "avi"])
    
    if uploaded_file:
       
        if st.session_state.transcript_text is not None:
             reset_states()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.read())
            st.session_state.audio_path = tmp.name
            st.session_state.audio_ready = True


if secenek == "Link gir":
    url = st.text_input("Video Linki")
    if url:
        if st.session_state.audio_ready: reset_states()
        
        with st.spinner("İndiriliyor..."):
            temp_dir = tempfile.mkdtemp()
            outtmpl = os.path.join(temp_dir, "audio.%(ext)s")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [{"key": "FFmpegExtractAudio","preferredcodec": "mp3"}],
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                for f in os.listdir(temp_dir):
                    if f.endswith(".mp3"):
                        st.session_state.audio_path = os.path.join(temp_dir, f)
                        st.session_state.audio_ready = True
            except Exception as e:
                st.error(str(e))

if st.session_state.audio_ready:
    if st.button("Transkripti Başlat"):
        if st.session_state.audio_path:
            try:
                with st.spinner("Yapay zeka dinliyor... Bu işlem dosya boyutuna göre zaman alabilir."):
                    final_text = transcribe_large_file(st.session_state.audio_path)
                    st.session_state.transcript_text = final_text
                    st.success("İşlem başarıyla tamamlandı!")
            except Exception as e:
                st.error(f"Hata oluştu: {e}")


if st.session_state.transcript_text:
    st.divider()
    st.subheader("📝 Sonuç")
    st.text_area("Metin", st.session_state.transcript_text, height=400)
    st.download_button("Metni İndir (.txt)", st.session_state.transcript_text, "transkript.txt")
