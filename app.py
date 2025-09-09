# app.py
# Streamlit UI for: "Calendar Gen — generate an ics for your calendar from photos, pdfs or text"
# Run: streamlit run app.py

import io
import json
import streamlit as st
import time
from math import floor

import parser as backend
import ics_gen                    

APP_TITLE = "Calendar Gen"
st.set_page_config(page_title=APP_TITLE, page_icon="🗓️", layout="centered")
st.title("🗓️ Calendar Gen")
st.caption("Generate an .ics for your calendar from **PDFs** or **text**.")

# Inputs
uploaded = st.file_uploader("Upload a **PDF** or **TXT**", type=["pdf", "txt"])
txt = st.text_area("Or paste your schedule text", height=240, placeholder="Paste timetable text here...")
default_filename = st.text_input("File name (optional, without .ics)", value="calendar")



########## Rate limiting api calls ###################

LIMIT = 5
WINDOW_SECONDS = 3600
TOKEN_REFILL_TIME = WINDOW_SECONDS / LIMIT  # 720s

@st.cache_data
def get_rate_limit_state():
    return {"tokens": LIMIT, "last_refill": time.time()}

rate_state = get_rate_limit_state()

def refill_tokens():
    now = time.time()
    elapsed = now - rate_state["last_refill"]
    add = floor(elapsed / TOKEN_REFILL_TIME)
    if add > 0:
        rate_state["tokens"] = min(LIMIT, rate_state["tokens"] + add)
        rate_state["last_refill"] += add * TOKEN_REFILL_TIME

def seconds_until_next_token():
    now = time.time()
    elapsed = now - rate_state["last_refill"]
    remaining = TOKEN_REFILL_TIME - (elapsed % TOKEN_REFILL_TIME)
    return int(remaining)


refill_tokens()

#######################################

if st.button("✨ Generate .ics"):
    # 1) Gather raw text
    raw_text = ""

    if uploaded is not None:
        suffix = uploaded.name.lower().rsplit(".", 1)[-1]
        if suffix == "txt":
            raw_text = uploaded.read().decode("utf-8", errors="ignore")

        elif suffix == "pdf":
                try:
                    uploaded.seek(0)
                    raw_text = backend.parse_pdf(uploaded)
                except Exception as e:
                    st.error(f"PDF parsing failed: {e}")
                    st.stop()

        else:
            st.error("Unsupported file type.")
            st.stop()

    if txt.strip():
        raw_text = (raw_text + "\n" + txt).strip() if raw_text else txt.strip()

    if not raw_text:
        st.warning("Please upload a PDF/TXT or paste some text.")
        st.stop()

    if not backend or not hasattr(backend, "create_events"):
        st.error("parser.create_events is not available. Make sure parser.py is in the same folder.")
        st.stop()

    # 2) Call your LLM-backed parser to get JSON (string or dict)
    try:
        result = backend.create_events(raw_text)
    except Exception as e:
        st.error(f"create_events failed: {e}")
        st.stop()

    # Show what came back
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
        st.subheader("Parsed JSON")
        st.json(parsed)
    except Exception:
        # If it's not valid JSON, show the raw text for debugging
        st.error("The backend did not return valid JSON.")
        st.code(str(result))
        st.stop()

    # 3) Convert JSON -> events -> calendar using your ics_gen backend
    try:
        # ics_gen.json_to_events expects a JSON string: pass through or dump
        payload = result if isinstance(result, str) else json.dumps(parsed)
        events = ics_gen.json_to_events(payload)
        if not events:
            st.error("No valid events found in parsed JSON.")
            st.stop()
        cal = ics_gen.add_events_to_calendar(events)
    except Exception as e:
        st.error(f"Error converting to calendar: {e}")
        st.stop()

    # 4) Offer download (no filesystem writes from the UI)
    ics_bytes = io.BytesIO()
    ics_bytes.write("".join(cal.serialize_iter()).encode("utf-8"))
    ics_bytes.seek(0)

    filename = (parsed.get("filename") if isinstance(parsed, dict) else None) or default_filename or "calendar"
    st.success("ICS generated!")
    st.download_button(
        label="⬇️ Download .ics",
        data=ics_bytes,
        file_name=f"{filename}.ics",
        mime="text/calendar"
    )

st.markdown("---")
st.subheader("ℹ️ Notes & Tips")

# Create a visually distinct container
with st.container():
    st.markdown(
        """
        <div style="background-color:#1f2123; padding:15px; border-radius:10px; border:1px solid #d0d7de;">
            <p>⚠️ <strong>Current Limitations:</strong></p>
            <ul>
                <li>This version <strong>only works with written schedules</strong> (text or PDFs).</li>
                <li>Image-based timetables are <em>not supported yet</em> — feature coming soon!</li>
            </ul>
            <br>
            <p>⏳ <strong>Usage Limit:</strong></p>
            <ul>
                <li>You are limited to <strong>5 uploads per hour</strong> to avoid excessive API costs.</li>
            </ul>
            <br>
            <p>💡 <strong>Tips for Best Results:</strong></p>
            <ul>
                <li>If your generated calendar looks off, try uploading a cleaner PDF or a plain text version of your schedule.</li>
                <li>Double-check unusual class times or skipped weeks before importing to Google or Apple Calendar.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

