import threading
import time
import av
import cv2
import face_recognition
import streamlit as st
import streamlit.components.v1 as components
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

from db import load_faces, save_face

st.set_page_config(page_title="Face Greeter", layout="wide")
st.title("🎭 Face Greeter (Web)")

ABSENT_TIMEOUT = 2.0
UNKNOWN_COOLDOWN = 30.0


class FaceProcessor(VideoProcessorBase):
    """Per-WebRTC-session processor. State lives on the instance, not in globals."""

    def __init__(self):
        self.lock = threading.Lock()
        self.present = {}                 # name -> last_seen timestamp
        self.greet_queue = []             # names waiting to be greeted
        self.unknown_encoding = None      # encoding of an unknown face (one-shot)
        self.skip_unknown_until = 0.0     # cooldown after skip
        self.known_names, self.known_encodings = load_faces()

    def reload_faces(self):
        n, e = load_faces()
        with self.lock:
            self.known_names = n
            self.known_encodings = e

    def pop_events(self):
        """Called from the main thread: drain queues and return."""
        with self.lock:
            greetings = list(self.greet_queue)
            self.greet_queue.clear()
            enc = self.unknown_encoding
            self.unknown_encoding = None
        return greetings, enc

    def skip_unknown_for(self, seconds: float):
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
                            # absent -> present transition: queue a greeting
                            self.greet_queue.append(name)

            if name == "Unknown":
                with self.lock:
                    if now > self.skip_unknown_until:
                        self.unknown_encoding = enc
                        self.skip_unknown_until = now + UNKNOWN_COOLDOWN

            cv2.rectangle(img, (left, top), (right, bottom), color, 2)
            cv2.putText(img, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Expire absent people so they can be greeted again next visit
        with self.lock:
            for n in list(self.present.keys()):
                if n not in seen and now - self.present[n] > ABSENT_TIMEOUT:
                    del self.present[n]

        return av.VideoFrame.from_ndarray(img, format="bgr24")


ctx = webrtc_streamer(
    key="face-greeter",
    video_processor_factory=FaceProcessor,
    media_stream_constraints={"video": True, "audio": False},
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
)

if "pending_enc" not in st.session_state:
    st.session_state.pending_enc = None


@st.fragment(run_every="1s")
def live_events():
    """Re-runs every second to poll the processor for greetings / unknown faces."""
    proc = ctx.video_processor
    if proc is None:
        st.info("Click **Start** above to enable the camera.")
        return

    greetings, enc = proc.pop_events()

    # ---- Greet known faces (visual toast + browser TTS) ----
    for name in greetings:
        st.toast(f"👋 Hello, {name}!")
        components.html(f"""
            <script>
            try {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(
                    "Hello {name}, nice to see you again!"
                );
                u.rate = 1.0;
                window.speechSynthesis.speak(u);
            }} catch(e) {{}}
            </script>
        """, height=0)

    # ---- Capture unknown face (do not overwrite a pending one) ----
    if enc is not None and st.session_state.pending_enc is None:
        st.session_state.pending_enc = enc

    # ---- Enrollment UI for the unknown face ----
    if st.session_state.pending_enc is not None:
        st.warning("👋 I don't think we've met. What's your name?")
        name = st.text_input("Your name:", key="enroll_name")
        col1, col2 = st.columns(2)

        if col1.button("Remember me", key="remember_btn"):
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

        if col2.button("Skip", key="skip_btn"):
            st.session_state.pending_enc = None
            proc.skip_unknown_for(30)


if ctx.state.playing:
    live_events()