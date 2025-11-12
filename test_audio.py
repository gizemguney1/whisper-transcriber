import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import ffmpeg
import shutil


# --- FFmpeg kontrolü ---
if shutil.which("ffmpeg") is None:
    st.error("⚠️ FFmpeg sistemde yüklü değil. Lütfen 'sudo apt-get install ffmpeg' komutunu çalıştırın.")
    st.stop()

# --- OpenAI API Anahtarı kontrolü ---
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("Lütfen Streamlit secrets ayarlarınıza OPENAI_API_KEY ekleyin.")
    st.stop()


# --- Başlık ---
st.title("🎧 Ses / Video Transkript Uygulaması")
st.write("Bir dosya yükleyin veya YouTube / Instagram / TikTok linki girin, biz metne çevirelim!")

# --- State başlangıcı ---
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = ""
if "url" not in st.session_state:
    st.session_state.url = ""


# --- Temizle butonu ---
if st.button("🗑️ Temizle"):
    st.session_state.transcript_text = ""
    st.session_state.url = ""
    st.info("Alanlar temizlendi.")

# --- Link alanı ---
st.session_state.url = st.text_input("🔗 Video veya ses linkini girin:", st.session_state.url)

# --- İşlem butonu ---
if st.button("🎙️ Transkripti Başlat"):
    if st.session_state.url.strip() == "":
        st.warning("Lütfen geçerli bir link girin.")
    else:
        with st.spinner("Ses indiriliyor ve çözümleniyor..."):
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": os.path.join(tmp_dir, "download.%(ext)s"),
                        "quiet": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([st.session_state.url])

                    audio_path = None
                    for f in os.listdir(tmp_dir):
                        if f.endswith((".mp3", ".m4a", ".wav", ".mp4")):
                            audio_path = os.path.join(tmp_dir, f)
                            break

                    if not audio_path:
                        st.error("Ses dosyası bulunamadı.")
                    else:
                        with open(audio_path, "rb") as audio_file:
                            transcript = client.audio.transcriptions.create(
                                model="gpt-4o-mini-transcribe",
                                file=audio_file
                            )
                            st.session_state.transcript_text = transcript.text
                            st.success("✅ Transkripsiyon tamamlandı!")

            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

# --- Transkript gösterimi ---
if st.session_state.transcript_text:
    st.subheader("📝 Çözülmüş Metin:")
    st.text_area("Transkript", st.session_state.transcript_text, height=300)
    st.download_button(
        "💾 Transkripti İndir",
        st.session_state.transcript_text,
        file_name="transkript.txt"
    )
