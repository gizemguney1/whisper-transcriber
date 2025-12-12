import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp

# ------------------ KONTROLLER ------------------
# FFmpeg yüklü mü kontrolü (Youtube indirme ve format işlemleri için gerekli)
if os.system("ffmpeg -version") != 0:
    st.error("FFmpeg bulunamadı. Lütfen sisteme FFmpeg yükleyin.")
    st.stop()

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("OPENAI_API_KEY eksik. Lütfen secrets.toml dosyasını kontrol et.")
    st.stop()

st.title("Ses / Video Transkript Uygulaması (Limitsiz Mod)")

# ------------------ STATE YÖNETİMİ ------------------
def reset_states():
    st.session_state.transcript_text = None
    st.session_state.audio_path = None
    st.session_state.audio_ready = False

if "transcript_text" not in st.session_state:
    reset_states()

# ------------------ ARAYÜZ (UI) ------------------
secenek = st.radio("İşlem türü:", ["Dosya yükle", "Link gir"], horizontal=True)

# ---------- DOSYA YÜKLEME ----------
if secenek == "Dosya yükle":
    uploaded_file = st.file_uploader(
        "Dosya yükle",
        type=["mp3", "wav", "m4a", "mp4", "mov", "avi", "ogg", "opus"]
    )

    if uploaded_file:
        # Eski dosya varsa ve yeni yükleme yapılıyorsa state'i sıfırla
        if st.session_state.transcript_text is not None:
             reset_states()
             
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.read())
            st.session_state.audio_path = tmp.name
            st.session_state.audio_ready = True

# ---------- LINK GİRME ----------
if secenek == "Link gir":
    url = st.text_input("Video linki")

    if url:
        # Yeni bir URL girildiyse önceki sonuçları temizle
        if st.session_state.audio_ready: 
             reset_states()

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

# ------------------ TRANSKRİPT İŞLEMİ ------------------
if st.session_state.audio_ready and st.session_state.transcript_text is None:
    # Eğer dosya hazırsa ama transkript yoksa işlemi başlat
    if st.session_state.audio_path:
        st.info(f"İşleniyor: {st.session_state.audio_path}")
        
        with st.spinner("Whisper transkript oluşturuyor..."):
            try:
                # Sıkıştırma fonksiyonu kaldırıldı, direkt dosya açılıyor
                with open(st.session_state.audio_path, "rb") as audio:
                    result = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio
                    )

                st.session_state.transcript_text = result.text
                st.success("🎉 Transkript hazır!")

            except Exception as e:
                st.error(f"Whisper hata verdi: {e}")
                st.warning("Not: OpenAI API tek seferde maksimum 25 MB dosya kabul eder. Dosyanız bundan büyük olabilir.")

# ------------------ SONUÇ GÖSTERİMİ ------------------
if st.session_state.transcript_text:
    st.subheader("📝 Transkript")
    st.text_area("Metin", st.session_state.transcript_text, height=300)

    st.download_button(
        label="Transkripti indir (.txt)",
        data=st.session_state.transcript_text,
        file_name="transkript.txt",
        mime="text/plain"
    )
