"""Streamlit chat UI for the real-estate sales assistant."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import get_settings

settings = get_settings()

INITIAL_REPLY = "Hi, it’s lovely to connect. Are you looking to buy, sell, or just explore your options right now?"

st.set_page_config(
    page_title="Aria | Real Estate AI Sales Assistant",
    page_icon="🏡",
    layout="centered",
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": INITIAL_REPLY}]

if "latest_payload" not in st.session_state:
    st.session_state.latest_payload = None


def _remove_last_user_message(expected_content: str) -> None:
    if not st.session_state.messages:
        return
    last_message = st.session_state.messages[-1]
    if (
        last_message.get("role") == "user"
        and last_message.get("content") == expected_content
    ):
        st.session_state.messages.pop()


st.title("Aria")
st.caption("Warm, premium lead qualification for real-estate conversations.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Tell Aria what you’re looking for")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    try:
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("Aria is thinking...")

            response = requests.post(
                f"{settings.backend_url}/chat",
                json={"messages": st.session_state.messages},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            st.session_state.latest_payload = payload

            st.session_state.messages.append(
                {"role": "assistant", "content": payload["reply"]}
            )
            thinking_placeholder.empty()
            st.write(payload["reply"])

        if payload["status"] == "completed":
            st.success("Lead is ready for follow-up.")
    except requests.HTTPError:
        _remove_last_user_message(prompt)
        try:
            detail = response.json().get("detail", "The backend returned an error.")
        except ValueError:
            detail = response.text or "The backend returned an error."
        st.error(detail)
    except requests.RequestException:
        _remove_last_user_message(prompt)
        st.error(
            "The backend is unavailable. Start the FastAPI server at "
            f"`{settings.backend_url}` and try again."
        )

with st.sidebar:
    st.subheader("Session")
    if st.button("Start new conversation", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_REPLY}]
        st.session_state.latest_payload = None
        st.rerun()

    payload = st.session_state.latest_payload
    if payload:
        st.caption(f"Status: {payload['status']}")
        if payload.get("suggested_meeting_date"):
            st.write(f"Suggested meeting: {payload['suggested_meeting_date']}")
