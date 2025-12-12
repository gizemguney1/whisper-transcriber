import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import uuid
import shutil

# ------------------ KONTROLLER ------------------
if os.system("ffmpeg -version") != 0:
    st.error("FFmpeg bulunamadı.")
    st.stop()

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("OPENAI_API_KEY eksik.")
    st.stop()

# ------------------ AYARLAR ------------------
MAX_MB = 25
MAX_BYTES = MAX_MB * 1024 * 1024

st.title("Ses / Video Transkript Uygulaması")

# ------------------ STATE ------------------
def reset_states():
    st.session_state.transcript_text = None
    st.session_state.translated_text = None
    st.session_state.audio_path = None
    st.session_state.audio_ready = False

if "transcript_text" not in st.session_state:
    reset_states()

# ------------------ FONKSİYONLAR ------------------
def compress_audio(input_path):
    output_path = f"{input_path}_compressed_{uuid.uuid4().hex}.mp3"
    cmd = f'ffmpeg -y -i "{input_path}" -ac 1 -ar 16000 -b:a 48k "{output_path}"'
    os.system(cmd)
    return output_path

def split_audio(input_path, duration=600):
    temp_dir = tempfile.mkdtemp()
    output_pattern = os.path.join(temp_dir, "chunk_%03d.mp3")
    cmd = f'''
    ffmpeg -y -i "{input_path}" -f segment -segment_time {duration} \
    -ac 1 -ar 16000 -b:a 48k "{output_pattern}"
    '''
    os.system(cmd)

    return sorted([
        os.path.join(temp_dir, f)
        for f in os.listdir(temp_dir)
        if f.endswith(".mp3")
    ])

# ------------------ UI ------------------
secenek = st.radio("İşlem türü:", ["Dosya yükle", "Link gir"], horizontal=True)

# ---------- DOSYA ----------
if secenek == "Dosya yükle":
    uploaded_file = st.file_uploader(
        "Dosya yükle",
        type=["mp3", "wav", "m4a", "mp4", "mov", "avi", "ogg", "opus"]
    )

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.read())
            st.session_state.audio_path = tmp.name
            st.session_state.audio_ready = True

# ---------- LINK ----------
if secenek == "Link gir":
    url = st.text_input("Video linki")

    if url:
        with st.spinner("Medya indiriliyor..."):
            temp_dir = tempfile.mkdtemp()
            outtmpl = os.path.join(temp_dir, "audio.%(ext)s")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                for f in os.listdir(temp_dir):
                    if f.endswith(".mp3"):
                        st.session_state.audio_path = os.path.join(temp_dir, f)
                        st.session_state.audio_ready = True
                        break

            except Exception as e:
                st.error(f"İndirme hatası: {e}")

# ------------------ TRANSKRİPT ------------------
if st.session_state.audio_ready and st.session_state.transcript_text is None:
    with st.spinner("Transkript oluşturuluyor..."):
        audio_path = st.session_state.audio_path
        audio_files = []

        if os.path.getsize(audio_path) > MAX_BYTES:
            compressed = compress_audio(audio_path)

            if os.path.getsize(compressed) <= MAX_BYTES:
                audio_files = [compressed]
            else:
                st.warning("Dosya büyük, parçalara bölünüyor...")
                audio_files = split_audio(compressed)
        else:
            audio_files = [audio_path]

        full_text = ""

        for i, path in enumerate(audio_files):
            st.info(f"Parça {i+1}/{len(audio_files)} işleniyor...")
            with open(path, "rb") as audio:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
                full_text += result.text + "\n"

        st.session_state.transcript_text = full_text
        st.success("🎉 Transkript hazır!")

# ------------------ GÖSTER ------------------
if st.session_state.transcript_text:
    st.subheader("📝 Transkript")
    st.text_area("Metin", st.session_state.transcript_text, height=300)

    st.download_button(
        "Transkripti indir",
        st.session_state.transcript_text,
        "transkript.txt"
    )

    if st.button("Türkçeye Çevir"):
        with st.spinner("Çevriliyor..."):
            tr = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator."},
                    {"role": "user", "content": st.session_state.transcript_text}
                ]
            )
            st.session_state.translated_text = tr.choices[0].message.content

if st.session_state.translated_text:
    st.subheader("🇹🇷 Türkçe")
    st.text_area("Çeviri", st.session_state.translated_text, height=300)
