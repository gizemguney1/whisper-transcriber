import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import uuid

# ------------------ KONTROLLER ------------------
if os.system("ffmpeg -version") != 0:
    st.error("FFmpeg bulunamadı.")
    st.stop()

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("OPENAI_API_KEY eksik.")
    st.stop()

st.title("Ses / Video Transkript Uygulaması")

# ------------------ STATE ------------------
def reset_states():
    st.session_state.transcript_text = None
    st.session_state.audio_path = None
    st.session_state.audio_ready = False

if "transcript_text" not in st.session_state:
    reset_states()

# ------------------ AYAR ------------------
MAX_MB = 25
MAX_BYTES = MAX_MB * 1024 * 1024

# ------------------ SIKISTIRMA (OPSİYONEL) ------------------
def compress_audio_if_needed(input_path):
    size = os.path.getsize(input_path)

    if size <= MAX_BYTES:
        return input_path

    st.warning("Dosya 25 MB üzerinde, sıkıştırmayı deniyorum...")

    output_path = f"{input_path}_compressed_{uuid.uuid4().hex}.mp3"
    cmd = f'ffmpeg -y -i "{input_path}" -ac 1 -ar 16000 -b:a 48k "{output_path}"'
    os.system(cmd)

    return output_path  # boyutu ne olursa olsun döndür

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
    with st.spinner("Whisper transkript oluşturuyor..."):
        try:
            final_audio = compress_audio_if_needed(st.session_state.audio_path)

            with open(final_audio, "rb") as audio:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )

            st.session_state.transcript_text = result.text
            st.success("🎉 Transkript hazır!")

        except Exception as e:
            st.error(f"Whisper hata verdi: {e}")

# ------------------ GÖSTER ------------------
if st.session_state.transcript_text:
    st.subheader("📝 Transkript")
    st.text_area("Metin", st.session_state.transcript_text, height=300)

    st.download_button(
        "Transkripti indir (.txt)",
        st.session_state.transcript_text,
        "transkript.txt"
    )
