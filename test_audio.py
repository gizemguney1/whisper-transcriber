import streamlit as st
from openai import OpenAI
import tempfile
import os
import yt_dlp
import shutil


if os.system("ffmpeg -version") != 0:
    st.error("FFmpeg bulunamadı. Lütfen kurulumu kontrol edin.")
    st.stop()


if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("Lütfen Streamlit secrets içine OPENAI_API_KEY ekleyin.")
    st.stop()

st.title("Ses / Video Transkript Uygulaması")
st.write("Bir dosya yükleyin veya YouTube / Instagram / TikTok linki girin, biz metne çevirelim!")


def reset_states():
    st.session_state.transcript_text = None
    st.session_state.translated_text = None
    st.session_state.audio_ready = False
    st.session_state.audio_path = None

if "transcript_text" not in st.session_state:
    reset_states()

if "last_url" not in st.session_state:
    st.session_state.last_url = None

if "last_filename" not in st.session_state:
    st.session_state.last_filename = None



secenek = st.radio("İşlem türü seçin:", ["Dosya yükle", "Link gir"], horizontal=True)


if secenek == "Dosya yükle":
    uploaded_file = st.file_uploader(
        "Dosya yükle (mp3, mp4, wav, m4a, mov, avi, mpeg4)",
        type=["mp3", "mp4", "wav", "m4a", "mov", "avi", "mpeg4"]
    )

    if uploaded_file:

        if uploaded_file.name != st.session_state.last_filename:
            reset_states()
            st.session_state.last_filename = uploaded_file.name

        file_ext = os.path.splitext(uploaded_file.name)[1]

       
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(uploaded_file.read())
            st.session_state.audio_path = temp_file.name
            st.session_state.audio_ready = True


elif secenek == "Link gir":
    video_url = st.text_input("Video linkini buraya yapıştırın:")

    if video_url:
       
        if video_url != st.session_state.last_url:
            reset_states()
            st.session_state.last_url = video_url

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
                        "preferredquality": "192"
                    }],
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                audio_file = None
                for f in os.listdir(temp_dir):
                    if f.endswith(".mp3"):
                        audio_file = os.path.join(temp_dir, f)
                        break

                if audio_file:
                    st.success("Medya indirildi ve sese dönüştürüldü.")
                    st.session_state.audio_path = audio_file
                    st.session_state.audio_ready = True
                else:
                    st.error("Ses dosyası oluşturulamadı.")

            except Exception as err:
                err_str = str(err).lower()
                if "login" in err_str or "cookie" in err_str or "403" in err_str:
                    st.error("Instagram videosu giriş gerektiriyor. Bu içerik indirilemez.")
                else:
                    st.error(f"Medya indirilemedi: {err}")


if st.session_state.audio_ready and st.session_state.transcript_text is None:

    try:
        with st.spinner("Whisper modeli transkript oluşturuyor..."):
            with open(st.session_state.audio_path, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )

        st.session_state.transcript_text = transcript.text
        st.success("🎉 Transkript hazır!")

        
        try:
            shutil.rmtree(os.path.dirname(st.session_state.audio_path), ignore_errors=True)
        except:
            pass

    except Exception as e:
        st.error(f"Transkript oluşturulurken hata: {e}")


if st.session_state.transcript_text:
    st.subheader(" Transkript")
    st.text_area("Metin:", st.session_state.transcript_text, height=300)

    st.download_button(
        label="Transkripti indir (.txt)",
        data=st.session_state.transcript_text,
        file_name="transkript.txt",
        mime="text/plain"
    )

    if st.button("Türkçeye Çevir"):
        with st.spinner("Türkçeye çeviriliyor..."):
            translation = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator."},
                    {"role": "user", "content": f"Bu metni Türkçeye çevir:\n\n{st.session_state.transcript_text}"}
                ]
            )
            st.session_state.translated_text = translation.choices[0].message.content


if st.session_state.translated_text:
    st.subheader("🇹🇷 Türkçe Çeviri")
    st.text_area("Çevrilmiş Metin:", st.session_state.translated_text, height=300)

    st.download_button(
        label="Çeviriyi indir (.txt)",
        data=st.session_state.translated_text,
        file_name="transkript_turkce.txt",
        mime="text/plain"
    )
