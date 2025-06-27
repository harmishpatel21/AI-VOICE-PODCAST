import streamlit as st
import requests
import re
import os
import pathlib
import json

API_BASE = "http://localhost:8000/api"

st.title("YouTube Podcast Transcript Studio")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Extract Transcript", "Create Podcast Script", "Listen to Saved Podcast"])

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
        length = st.slider("Podcast Length (minutes)", min_value=5, max_value=30, value=10)
        if st.button("Generate Podcast Script"):
            with st.spinner("Generating podcast script using LLM..."):
                payload = {
                    "char1": char1,
                    "char2": char2,
                    "topic": topic,
                    "length_minutes": length,
                    "model": "mistral"
                }
                resp = requests.post(f"{API_BASE}/generate_podcast_script", json=payload)
                if resp.status_code == 200 and resp.json().get("script"):
                    st.subheader("Generated Podcast Script")
                    script = resp.json()["script"]
                    st.text_area("Script", script, height=600)
                    with st.expander("Show LLM Prompt"):
                        st.code(resp.json().get("prompt", ""))
                    # Narration section
                    st.markdown("---")
                    st.subheader("Narrate & Play Podcast Audio")
                    tts_option = st.radio("Select TTS Engine", ["ElevenLabs", "Bark"], horizontal=True)
                    if st.button("Narrate Podcast Audio"):
                        with st.spinner("Synthesizing podcast audio..."):
                            narrate_payload = {
                                "script": script,
                                "char1": char1,
                                "char2": char2,
                                "topic": topic
                            }
                            if tts_option == "ElevenLabs":
                                narrate_resp = requests.post(f"{API_BASE}/narrate_script", json=narrate_payload)
                            else:
                                narrate_resp = requests.post(f"{API_BASE}/narrate_script_bark", json=narrate_payload)
                            if narrate_resp.status_code == 200 and narrate_resp.json().get("audio_path"):
                                audio_path = narrate_resp.json()["audio_path"]
                                st.success("Podcast audio generated!")
                                st.audio(audio_path)
                            else:
                                st.error(f"Failed to generate audio: {narrate_resp.text}")
                else:
                    st.error(f"Failed to generate script: {resp.text}")

# --- Listen to Saved Podcast Page ---
if page == "Listen to Saved Podcast":
    st.header("Listen to Saved Podcast Audio or Narrate Again")
    base_dir = pathlib.Path("saved_scripts")
    if not base_dir.exists():
        st.info("No saved podcast scripts found.")
    else:
        topics = [d.name for d in base_dir.iterdir() if d.is_dir()]
        if not topics:
            st.info("No topics found.")
        else:
            selected_topic = st.selectbox("Select a topic", topics)
            topic_dir = base_dir / selected_topic
            script_files = sorted([f for f in topic_dir.glob("*.json")], key=os.path.getmtime, reverse=True)
            if not script_files:
                st.info("No scripts found for this topic.")
            else:
                selected_script = st.selectbox("Select a podcast script", [f.name for f in script_files])
                if selected_script:
                    script_path = topic_dir / selected_script
                    with open(script_path, 'r', encoding='utf-8') as f:
                        script_data = json.load(f)
                    st.markdown(f"**Characters:** {script_data['char1']} & {script_data['char2']}")
                    st.markdown(f"**Topic:** {script_data['topic']}")
                    st.markdown(f"**Generated at:** {script_data['timestamp']}")
                    st.text_area("Script", script_data.get("script", ""), height=400)
                    tts_option = st.radio("Select TTS Engine", ["ElevenLabs", "Bark"], horizontal=True, key=f"tts_option_{selected_script}")
                    if st.button("Narrate & Play This Script"):
                        with st.spinner("Synthesizing podcast audio..."):
                            narrate_payload = {
                                "topic": script_data.get("topic", ""),
                                "script": script_data.get("script", ""),
                                "char1": script_data.get("char1", ""),
                                "char2": script_data.get("char2", ""),
                                "topic": script_data.get("topic", ""),
                            }
                            if tts_option == "ElevenLabs":
                                narrate_resp = requests.post(f"{API_BASE}/narrate_script", json=narrate_payload)
                            else:
                                narrate_resp = requests.post(f"{API_BASE}/narrate_script_bark", json=narrate_payload)
                            if narrate_resp.status_code == 200 and narrate_resp.json().get("audio_path"):
                                audio_path = narrate_resp.json()["audio_path"]
                                st.success("Podcast audio generated!")
                                st.audio(audio_path)
                            else:
                                st.error(f"Failed to generate audio: {narrate_resp.text}")
