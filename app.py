import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re

# 페이지 설정
st.set_page_config(page_title="VidiSum - 유튜브 요약기", page_icon="🎥", layout="wide")

# CSS 스타일 주입 (디자인 수정 반영)
st.markdown("""
<style>
    /* 전체 기반 폰트 사이즈 */
    html {
        font-size: 20px;
    }

    /* 일반 텍스트 및 본문 폰트 크기 (대형 모드) */
    .stMarkdown p, .stMarkdown li, .stText, p, .stButton button, label {
        font-size: 2.2rem !important; 
        line-height: 1.6 !important;
    }

    /* 1. 사이드바 너비 대폭 확장 */
    section[data-testid="stSidebar"] {
        width: 450px !important;
    }

    /* 2. 사이드바 내부 텍스트 및 라벨 100% 축소 (일반 크기) */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox div,
    [data-testid="stSidebar"] .stAlert p {
        font-size: 1.0rem !important; 
    }
    
    /* 사이드바 제목 크기 축소 */
    [data-testid="stSidebar"] h2 {
        font-size: 1.4rem !important;
    }

    /* 3. 메인 제목 폰트 50% 축소 (4.5rem -> 2.2rem) */
    h1 { 
        font-size: 2.2rem !important; 
        padding-bottom: 1rem; 
        font-weight: bold;
    }

    /* 기타 요소 스타일 */
    h2 { font-size: 2.0rem !important; }
    h3 { font-size: 1.8rem !important; }
    button[data-testid="stTab"] p { font-size: 2.0rem !important; }
    .stTextInput input { font-size: 2.0rem !important; padding: 1rem !important; }
    .stTextArea textarea { font-size: 2.0rem !important; line-height: 1.8 !important; }
    
    .element-container { margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# 제목
st.title("🎥 VidiSum: 유튜브 자막 추출 및 요약")

# API 키 설정 (사이드바 - 개인용 기본값 설정)
DEFAULT_API_KEY = "AIzaSyBhmk9f8QqMLcUwR7vY7q5ZTXY63Vw-BIw" 

selected_model = "gemini-1.5-flash" 
with st.sidebar:
    st.header("설정")
    api_key = st.text_input(
        "Google Gemini API Key", 
        value=DEFAULT_API_KEY,
        type="password", 
        help="Google AI Studio에서 발급받은 키를 입력하세요."
    )
    
    if api_key:
        genai.configure(api_key=api_key)
        try:
            # 사용 가능한 모델 목록 가져오기
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model_options = [m.replace('models/', '') for m in models]
            
            default_index = 0
            if 'gemini-1.5-flash' in model_options:
                default_index = model_options.index('gemini-1.5-flash')
            
            selected_model = st.selectbox("AI 모델 선택", model_options, index=default_index)
            st.success(f"모델 연결 성공")
        except Exception as e:
            st.error(f"모델 목록을 불러올 수 없습니다: {e}")
    
    st.markdown("---")
    st.header("고급 설정")
    cookie_text = st.text_area(
        "YouTube Cookies (Netscape format)", 
        value="",
        height=150,
        help="유튜브 차단을 우회하기 위해 브라우저 확장 프로그램(Get cookies.txt 등)으로 추출한 쿠키를 입력하세요."
    )
    
    st.markdown("---")
    st.info("이 앱은 Streamlit과 Google Gemini를 사용하여 제작되었습니다.")

# 유튜브 비디오 ID 추출 함수 (개선됨)
def extract_video_id(url):
    # 다양한 유튜브 URL 패턴 지원 (shorts, youtu.be, watch?v= 등)
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/live\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# 자막 추출 함수 (Cookies 지원 추가)
def get_transcript(video_id, cookie_text=None):
    cookie_file = None
    try:
        # 쿠키가 제공된 경우 임시 파일로 저장하여 사용
        if cookie_text:
            import tempfile
            import os
            
            # 텍스트 형식의 쿠키를 netscape 형식으로 가정하거나 
            # 단순히 파일로 저장 (youtube-transcript-api가 요구하는 형식이어야 함)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tf:
                tf.write(cookie_text)
                cookie_file = tf.name
        
        # 1차 시도: 특정 언어 지정 fetch
        api = YouTubeTranscriptApi()
        
        # 쿠키 파일이 있으면 사용
        if cookie_file:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'], cookies=cookie_file)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        
        full_text = " ".join([t['text'] for t in transcript]).strip()
        
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
            
        return full_text
    except Exception as e:
        if cookie_file and os.path.exists(cookie_file):
            import os
            os.remove(cookie_file)
            
        error_msg = str(e)
        if "Cookies" in error_msg or "Login" in error_msg:
            return None, "유튜브에서 접근을 차단했습니다. 사이드바에 쿠키(Cookies)를 입력해보세요."
        return None, f"자막을 가져올 수 없습니다: {error_msg}"

# AI 요약 함수
def summarize_text(text, model_name):
    if not api_key:
        return "API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        다음 유튜브 동영상의 자막을 분석하여 한국어로 요약해 주세요.
        
        [지시사항]
        1. 전체 내용을 3~5문장으로 자연스럽게 요약하세요.
        2. 핵심 포인트 3~5개를 불렛포인트로 정리하세요.
        3. 톤앤매너는 명확하고 전문적인 어조를 유지하세요.

        [자막 내용]
        {text[:25000]} 
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"요약 중 오류 발생: {str(e)}"

# 메인 화면 UI
st.divider()

url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")

if url:
    video_id = extract_video_id(url)
    if video_id:
        st.video(url)
        
        if st.button("🚀 요약하기", type="primary", use_container_width=True):
            if not api_key:
                st.error("⬅️ 사이드바에서 API 키를 먼저 설정해주세요.")
            else:
                with st.spinner("자막 추출 및 분석 중..."):
                    transcript_result = get_transcript(video_id, cookie_text=cookie_text)
                    
                    if isinstance(transcript_result, tuple):
                        st.error(transcript_result[1])
                    else:
                        st.session_state['transcript'] = transcript_result
                        st.rerun()
    else:
        st.error("유효하지 않은 URL입니다.")

# 결과 출력 섹션
if 'transcript' in st.session_state:
    transcript = st.session_state['transcript']
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📝 AI 요약", "📄 전체 자막"])
    
    with tab1:
        if not api_key:
            st.warning("API 키가 설정되지 않아 요약을 생성할 수 없습니다.")
        else:
            with st.spinner("AI가 내용을 요약하고 있습니다..."):
                summary = summarize_text(transcript, selected_model)
                st.markdown(summary)
        
    with tab2:
        st.text_area("스크립트", transcript, height=600)
        
        # 자막 다운로드 버튼 유지
        file_name = f"transcript_{video_id}.txt" if 'video_id' in locals() else "transcript.txt"
        st.download_button(
            label="📄 자막 다운로드 (.txt)",
            data=transcript,
            file_name=file_name,
            mime="text/plain",
            use_container_width=True
        )