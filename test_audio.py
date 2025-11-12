import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import ffmpeg
import shutil


if shutil.which("ffmpeg") is None:
    st.error("FFmpeg sistemde yüklü değil. Lütfen 'sudo apt-get install ffmpeg' komutunu çalıştırın.")
    st.stop()


if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("Lütfen Streamlit secrets ayarlarınıza OPENAI_API_KEY ekleyin.")
    st.stop()

st.title("Ses / Video Transkript Uygulaması")
st.write("Bir dosya yükleyin veya link girin, metne çevirsin!")

# -------------------------------
# ✅ Session temizleme fonksiyonu
# -------------------------------
def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.clear()
    st.experimental_rerun()

if st.button("🔄 Yeni İşlem Başlat"):
    reset_session()


if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = None
if "audio_ready" not in st.session_state:
    st.session_state.audio_ready = False
if "translated_text" not in st.session_state:
    st.session_state.translated_text = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None


secenek = st.radio("İşlem türü seçin:", ["Dosya yükle", "Link gir"], horizontal=True)
temp_path = None
audio_path = None

try:
   
    if secenek == "Dosya yükle":
        uploaded_file = st.file_uploader(
            "Dosya yükle (mp3, mp4, wav, m4a, mov, avi, mpeg4)",
            type=["mp3", "mp4", "wav", "m4a", "mov", "avi", "mpeg4"]
        )
        if uploaded_file and not st.session_state.audio_ready:
            file_extension = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(uploaded_file.read())
                temp_path = temp_file.name
            audio_path = temp_path
            st.session_state.audio_ready = True
            st.session_state.audio_path = audio_path

  
    elif secenek == "Link gir":
        video_url = st.text_input("Video veya ses linkini buraya yapıştırın:")

        if video_url and not st.session_state.audio_ready:
            if video_url.startswith(":ps"):
                video_url = "https" + video_url[3:]

            with st.spinner("Medya indiriliyor..."):
                try:
                    temp_dir = tempfile.mkdtemp()
                    output_path = os.path.join(temp_dir, "audio.%(ext)s")

                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": output_path,
                        "quiet": True,
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }],
                    }

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])

                    for f in os.listdir(temp_dir):
                        if f.endswith(".mp3"):
                            audio_path = os.path.join(temp_dir, f)
                            break

                    if audio_path:
                        st.success("Medya indirildi ve sese dönüştürüldü.")
                        st.session_state.audio_ready = True
                        st.session_state.audio_path = audio_path
                    else:
                        st.error("Ses dosyası oluşturulamadı.")
                except Exception as err:
                    if "login required" in str(err).lower() or "cookies" in str(err).lower():
                        st.error("Instagram videolarını indirmek için giriş gerekiyor. Bu içerik indirilemez.")
                    else:
                        st.error(f"Medya indirilirken hata oluştu: {err}")

  
    if st.session_state.audio_ready and st.session_state.transcript_text is None:
        if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
            with st.spinner("Transkript oluşturuluyor..."):
                with open(st.session_state.audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                st.session_state.transcript_text = transcript.text
                st.success("Transkript tamamlandı.")

    
    if st.session_state.transcript_text:
        st.subheader("Transkript")
        st.text_area("Metin", st.session_state.transcript_text, height=300)
        st.download_button(
            label="Transkripti indir (.txt)",
            data=st.session_state.transcript_text,
            file_name="transkript.txt",
            mime="text/plain"
        )

        
        if st.button("Türkçeye Çevir"):
            with st.spinner("Türkçeye çevriliyor..."):
                translation = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional translator."},
                        {"role": "user", "content": f"Bu metni Türkçeye çevir:\n\n{st.session_state.transcript_text}"}
                    ]
                )
                st.session_state.translated_text = translation.choices[0].message.content

    
    if st.session_state.translated_text:
        st.subheader("Türkçe Çeviri")
        st.text_area("Çevrilmiş Metin", st.session_state.translated_text, height=300)
        st.download_button(
            label="Türkçe çeviriyi indir (.txt)",
            data=st.session_state.translated_text,
            file_name="transkript_turkce.txt",
            mime="text/plain"
        )

except Exception as e:
    st.error(f"Bir hata oluştu: {e}")

finally:
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass
