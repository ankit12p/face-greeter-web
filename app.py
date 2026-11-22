import threading
import time
import av
import cv2
import face_recognition
import streamlit as st
import streamlit.components.v1 as components
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

from db import load_faces, save_face, list_users

# ---------------------------------------------------------------- page config
st.set_page_config(
    page_title="Welcome to Pandeyji Ka App",
    page_icon="🎭",
    layout="wide",
)

ABSENT_TIMEOUT = 2.0
UNKNOWN_COOLDOWN = 30.0

# ---------------------------------------------------------------- custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');

/* ---------- page background ---------- */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 45%, #f093fb 100%) !important;
    background-attachment: fixed !important;
    font-family: 'Poppins', sans-serif;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none; }

/* ---------- hero banner ---------- */
.pg-hero {
    text-align: center;
    padding: 28px 20px;
    border-radius: 22px;
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    margin-bottom: 22px;
    border: 1px solid rgba(255,255,255,0.3);
}
.pg-hero h1 {
    font-size: 3rem;
    font-weight: 800;
    margin: 0;
    background: linear-gradient(90deg, #ffecd2, #fcb69f, #ffeaa7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: pgGlow 3s ease-in-out infinite alternate;
}
.pg-hero p {
    color: #ffffff;
    font-size: 1.15rem;
    margin-top: 10px;
    font-weight: 400;
    opacity: 0.95;
}
@keyframes pgGlow {
    from { filter: drop-shadow(0 0 8px rgba(255,236,210,0.5)); }
    to   { filter: drop-shadow(0 0 22px rgba(252,182,159,0.9)); }
}

/* ---------- stat cards ---------- */
.pg-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin: 10px 0 24px 0;
}
.pg-card {
    padding: 22px 18px;
    border-radius: 18px;
    color: #fff;
    text-align: center;
    box-shadow: 0 6px 20px rgba(0,0,0,0.18);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    border: 1px solid rgba(255,255,255,0.25);
}
.pg-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 28px rgba(0,0,0,0.28);
}
.pg-card .pg-icon  { font-size: 2rem; }
.pg-card .pg-value { font-size: 1.7rem; font-weight: 800; margin-top: 6px; }
.pg-card .pg-label { font-size: 0.9rem; opacity: 0.9; }
.pg-card.c1 { background: linear-gradient(135deg, #f857a6, #ff5858); }
.pg-card.c2 { background: linear-gradient(135deg, #00b09b, #96c93d); }
.pg-card.c3 { background: linear-gradient(135deg, #4776e6, #8e54e9); }
.pg-card.c4 { background: linear-gradient(135deg, #f7971e, #ffd200); color: #4a2800; }

/* ---------- section titles ---------- */
.pg-section {
    color: #ffffff;
    font-weight: 600;
    font-size: 1.15rem;
    margin: 6px 0 10px 0;
    padding-left: 12px;
    border-left: 5px solid #ffeaa7;
}

/* ---------- video box ---------- */
.st-key-video_box {
    border-radius: 20px !important;
    overflow: hidden !important;
    border: 3px solid rgba(255,255,255,0.45) !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35) !important;
    padding: 12px !important;
    background: rgba(255,255,255,0.08) !important;
    backdrop-filter: blur(10px) !important;
}

/* ---------- info panel ---------- */
.pg-info {
    color: #fff;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.25);
    padding: 16px 18px;
    border-radius: 16px;
    line-height: 1.7;
    font-size: 0.95rem;
    margin-bottom: 14px;
}
.pg-info strong { color: #ffeaa7; }

/* ---------- buttons ---------- */
.stButton > button {
    background: linear-gradient(90deg, #f857a6, #ff5858) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    box-shadow: 0 4px 14px rgba(248,87,166,0.45) !important;
    transition: all 0.25s ease !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 22px rgba(248,87,166,0.65) !important;
}

/* ---------- inputs ---------- */
.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 2px solid rgba(255,255,255,0.6) !important;
    background: rgba(255,255,255,0.92) !important;
    color: #222 !important;
    padding: 10px 14px !important;
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.1) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255,255,255,0.2);
}
[data-testid="stSidebar"] * { color: #ffffff !important; }

/* ---------- alerts ---------- */
.stAlert { border-radius: 14px !important; }

/* ---------- responsive ---------- */
@media (max-width: 768px) {
    .pg-hero h1 { font-size: 1.9rem; }
    .pg-hero p  { font-size: 0.95rem; }
    .pg-cards   { grid-template-columns: 1fr 1fr; }
    .pg-card .pg-value { font-size: 1.3rem; }
}
@media (max-width: 480px) {
    .pg-cards { grid-template-columns: 1fr; }
    .pg-hero h1 { font-size: 1.6rem; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- hero banner
st.markdown("""
<div class="pg-hero">
    <h1>🎭 Welcome to Pandeyji Ka App 🎉</h1>
    <p>Real-time Face Recognition &nbsp;·&nbsp; Instant Greetings &nbsp;·&nbsp; Smart Enrollment</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- processor
class FaceProcessor(VideoProcessorBase):
    """Per-WebRTC-session processor. State lives on the instance, not in globals."""

    def __init__(self):
        self.lock = threading.Lock()
        self.present = {}
        self.greet_queue = []
        self.unknown_encoding = None
        self.skip_unknown_until = 0.0
        self.known_names, self.known_encodings = load_faces()

    def reload_faces(self):
        n, e = load_faces()
        with self.lock:
            self.known_names = n
            self.known_encodings = e

    def pop_events(self):
        with self.lock:
            greetings = list(self.greet_queue)
            self.greet_queue.clear()
            enc = self.unknown_encoding
            self.unknown_encoding = None
        return greetings, enc

    def skip_unknown_for(self, seconds):
        with self.lock:
            self.skip_unknown_until = time.time() + seconds

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        small = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locs = face_recognition.face_locations(rgb_small)
        encs = face_recognition.face_encodings(rgb_small, locs)
        scaled_locs = [(t * 2, r * 2, b * 2, l * 2) for (t, r, b, l) in locs]

        now = time.time()
        seen = set()

        with self.lock:
            names = list(self.known_names)
            encodings = list(self.known_encodings)

        for (top, right, bottom, left), enc in zip(scaled_locs, encs):
            name, color = "Unknown", (0, 0, 255)

            if encodings:
                matches = face_recognition.compare_faces(encodings, enc, tolerance=0.5)
                if True in matches:
                    idx = matches.index(True)
                    name = names[idx]
                    color = (0, 255, 0)
                    seen.add(name)

                    with self.lock:
                        was_absent = name not in self.present
                        self.present[name] = now
                        if was_absent:
                            self.greet_queue.append(name)

            if name == "Unknown":
                with self.lock:
                    if now > self.skip_unknown_until:
                        self.unknown_encoding = enc
                        self.skip_unknown_until = now + UNKNOWN_COOLDOWN

            cv2.rectangle(img, (left, top), (right, bottom), color, 2)
            cv2.putText(img, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        with self.lock:
            for n in list(self.present.keys()):
                if n not in seen and now - self.present[n] > ABSENT_TIMEOUT:
                    del self.present[n]

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## 📖 How it works")
    st.markdown("""
    1. Click **Start** and allow camera access.
    2. The app detects faces and draws boxes.
    3. **Known face** → greeted with toast + voice.
    4. **Unknown face** → asked for name, then remembered.
    5. Leave the frame for 3 s to reset the greeting.
    """)
    st.markdown("---")
    st.markdown("## 🎯 Tips")
    st.markdown("""
    - Look straight at the camera
    - Good lighting improves accuracy
    - One face at a time for enrollment
    """)
    st.markdown("---")
    st.markdown("Made with ❤️ by **Pandeyji**")


# ---------------------------------------------------------------- stat cards
@st.fragment(run_every="2s")
def render_stats():
    try:
        total = len(list_users())
    except Exception:
        total = 0
    st.markdown(f"""
    <div class="pg-cards">
        <div class="pg-card c1">
            <div class="pg-icon">👥</div>
            <div class="pg-value">{total}</div>
            <div class="pg-label">Registered Faces</div>
        </div>
        <div class="pg-card c2">
            <div class="pg-icon">🎥</div>
            <div class="pg-value">Live</div>
            <div class="pg-label">Camera Stream</div>
        </div>
        <div class="pg-card c3">
            <div class="pg-icon">⚡</div>
            <div class="pg-value">Real-time</div>
            <div class="pg-label">Recognition</div>
        </div>
        <div class="pg-card c4">
            <div class="pg-icon">🎙️</div>
            <div class="pg-value">Voice</div>
            <div class="pg-label">Greeting Enabled</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


render_stats()

# ---------------------------------------------------------------- main layout
left, right = st.columns([3, 1], gap="large")

with left:
    st.markdown('<div class="pg-section">🎥 Live Camera</div>', unsafe_allow_html=True)
    with st.container(key="video_box"):
        ctx = webrtc_streamer(
            key="face-greeter",
            video_processor_factory=FaceProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        )

with right:
    st.markdown('<div class="pg-section">💡 Quick Tips</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="pg-info">
    <strong>Face the camera</strong> directly for best accuracy.<br>
    <strong>Leave the frame</strong> for ~3 s to be greeted again.<br>
    <strong>Unknown faces</strong> get asked a name automatically.<br>
    <strong>Audio</strong> needs one click on the page first.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pg-section">👥 Registered</div>', unsafe_allow_html=True)

    @st.fragment(run_every="3s")
    def render_users():
        try:
            users = list_users()
        except Exception:
            users = []
        if users:
            st.markdown(
                "\n".join(f"- 🟢 **{u}**" for u in users)
            )
        else:
            st.markdown("_No one registered yet._")

    render_users()


# ---------------------------------------------------------------- events
if "pending_enc" not in st.session_state:
    st.session_state.pending_enc = None


@st.fragment(run_every="1s")
def live_events():
    proc = ctx.video_processor
    if proc is None:
        return

    greetings, enc = proc.pop_events()

    for name in greetings:
        st.toast(f"👋 Hello, {name}!", icon="🎉")
        components.html(f"""
            <script>
            try {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(
                    "Hello {name}, welcome to Pandeyji Ka App!"
                );
                u.rate = 1.0;
                window.speechSynthesis.speak(u);
            }} catch(e) {{}}
            </script>
        """, height=0)

    if enc is not None and st.session_state.pending_enc is None:
        st.session_state.pending_enc = enc

    if st.session_state.pending_enc is not None:
        st.markdown('<div class="pg-section">🆕 New Face Detected</div>',
                    unsafe_allow_html=True)
        st.warning("👋 I don't think we've met. What's your name?")
        name = st.text_input("Your name:", key="enroll_name")
        c1, c2 = st.columns(2)

        if c1.button("✅ Remember me", key="remember_btn"):
            n = name.strip()
            with proc.lock:
                existing = list(proc.known_names)
            if not n:
                st.error("Please enter a name.")
            elif n in existing:
                st.info(f"I already know someone called {n}.")
                st.session_state.pending_enc = None
            else:
                save_face(n, st.session_state.pending_enc)
                proc.reload_faces()
                st.session_state.pending_enc = None
                st.success(f"Nice to meet you, {n}!")
                st.balloons()

        if c2.button("⏭️ Skip", key="skip_btn"):
            st.session_state.pending_enc = None
            proc.skip_unknown_for(30)


if ctx.state.playing:
    live_events()