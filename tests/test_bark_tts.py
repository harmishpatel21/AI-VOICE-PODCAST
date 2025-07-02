import torch
from bark import SAMPLE_RATE, generate_audio
from pydub import AudioSegment
import re
import tempfile
import numpy as np
import shutil

# List of English Bark presets to try
english_presets = [
    "v2/en_speaker_0",
    "v2/en_speaker_1",
    "v2/en_speaker_2",
    "v2/en_speaker_3",
    "v2/en_speaker_4",
    "v2/en_speaker_5",
    "v2/en_speaker_6",
    "v2/en_speaker_7"
]

# Sentences to test
english_text = "Hello, [laugh] my name is Bark and I love open source AI."

hindi_preset = "v2/hi_speaker_0"

# Speed factor (1.0 = normal, >1.0 = faster)
speedup = 1.2

def speedup_audio(audio_segment, speed=1.2):
    # Use pydub to speed up audio without changing pitch too much
    return audio_segment._spawn(audio_segment.raw_data, overrides={
        "frame_rate": int(audio_segment.frame_rate * speed)
    }).set_frame_rate(audio_segment.frame_rate)

# Check and print GPU status
if torch.cuda.is_available():
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    print("Using CPU (will be slow)")

# Try all English presets
for preset in english_presets:
    # text_clean = re.sub(r"\[[^\]]*\]", "", english_text).strip()
    text_clean = english_text.strip()
    print(f"Generating audio for preset: {preset} (GPU: {torch.cuda.is_available()})")
    audio_array = generate_audio(text_clean, history_prompt=preset)
    audio_int16 = (audio_array * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
        seg = AudioSegment(
            audio_int16.tobytes(),
            frame_rate=SAMPLE_RATE,
            sample_width=2,
            channels=1
        )
        seg_fast = speedup_audio(seg, speedup)
        seg_fast.export(tf.name, format="wav")
        out_file = f"bark_test_output_{preset.replace('/', '_')}_fast.wav"
        shutil.copy(tf.name, out_file)
        print(f"Audio saved to: {out_file}")

# Try Hindi preset
print(f"Generating Hindi audio for preset: {hindi_preset} (GPU: {torch.cuda.is_available()})")
hindi_array = generate_audio(hindi_text, history_prompt=hindi_preset)
hindi_int16 = (hindi_array * 32767).astype(np.int16)
with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
    seg = AudioSegment(
        hindi_int16.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,
        channels=1
    )
    seg_fast = speedup_audio(seg, speedup)
    seg_fast.export(tf.name, format="wav")
    out_file = f"bark_test_output_{hindi_preset.replace('/', '_')}_fast.wav"
    shutil.copy(tf.name, out_file)
    print(f"Hindi audio saved to: {out_file}")
