import streamlit as st
import requests
import re

API_BASE = "http://localhost:8000/api"

st.title("YouTube Podcast Transcript Studio")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Extract Transcript", "Create Podcast Script"])

# --- Extract Transcript Page ---
if page == "Extract Transcript":
    st.header("Extract YouTube Transcript")
    st.write("Enter a YouTuber's channel name or URL to fetch video transcripts.")
    youtuber = st.text_input("YouTuber Channel Name or URL", "@samayrainaofficial")
    num_videos = st.number_input("Number of latest videos", min_value=1, max_value=20, value=3)
    if st.button("Fetch Transcripts"):
        with st.spinner("Fetching video list and transcripts via API..."):
            resp = requests.get(f"{API_BASE}/channel_videos", params={"youtuber": youtuber, "num_videos": num_videos})
            video_ids = resp.json() if resp.status_code == 200 else []
            if not video_ids:
                st.error("No videos found for this channel.")
            else:
                for vid in video_ids:
                    st.markdown(f"### Video: https://youtu.be/{vid}")
                    data = requests.get(f"{API_BASE}/transcript", params={"video_id": vid}).json()
                    if data and data.get("transcript"):
                        lang = data.get("language", "?")
                        gen = "Auto-generated" if data.get("is_generated") else "Manual"
                        st.text_area(f"Transcript ({lang}, {gen})", data["transcript"], height=200)
                    else:
                        st.warning(f"Transcript not available: {data.get('error') if data else 'Unknown error'}")
    st.write("Or, provide a direct YouTube video link to fetch its transcript.")
    video_url = st.text_input("YouTube Video URL (optional)", "")
    if st.button("Fetch Transcript from Video Link") and video_url:
        with st.spinner("Fetching transcript via API..."):
            data = requests.get(f"{API_BASE}/transcript_from_url", params={"video_url": video_url}).json()
            if data and data.get("transcript"):
                lang = data.get("language", "?")
                gen = "Auto-generated" if data.get("is_generated") else "Manual"
                st.markdown(f"### Video: {video_url}")
                st.text_area(f"Transcript ({lang}, {gen})", data["transcript"], height=200)
            else:
                st.warning(f"Transcript not available: {data.get('error') if data else 'Unknown error'}")

# --- Create Podcast Script Page ---
if page == "Create Podcast Script":
    st.header("Create Podcast Script from Saved Transcripts")
    # List available youtubers
    yt_resp = requests.get(f"{API_BASE}/list_youtubers")
    youtubers = yt_resp.json() if yt_resp.status_code == 200 else []
    if len(youtubers) < 2:
        st.warning("At least two youtubers with transcripts are required.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            char1 = st.selectbox("Select Character 1", youtubers, key="char1")
        with col2:
            char2 = st.selectbox("Select Character 2", [y for y in youtubers if y != st.session_state.get('char1')], key="char2")
        topic = st.text_input("Podcast Topic", "comedy")
        if st.button("Generate Podcast Script"):
            st.info("Podcast script generation coming soon! (LLM integration)")
