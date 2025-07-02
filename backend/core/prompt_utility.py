def get_podcast_script_prompt(char1: str, char2: str, char1_samples: list, char2_samples: list, topic: str, length_minutes: int, script_language: str) -> str:
    """
    Generates the prompt for creating a podcast script.
    """
    return f"""
You are an expert podcast scriptwriter. Write a realistic, engaging, and natural-sounding podcast conversation between two hosts:

- {char1}: Here are some example lines in their style: {char1_samples}
- {char2}: Here are some example lines in their style: {char2_samples}

The topic of the podcast is: \"{topic}\".

Alternate their dialogue naturally, making sure each host's personality and style comes through. The conversation should be about {length_minutes} minutes long (roughly 1500-2000 words). Use humor, depth, and storytelling as appropriate. Start with a brief introduction, then dive into the topic, and end with a natural outro.

**Important:** For each line of dialogue, add a short expression or action in square brackets that describes how the host is speaking, reacting, or gesturing (e.g., [laughs], [smiling], [thoughtful pause], [raises eyebrow], [enthusiastic], [shrugs], etc.). These expressions should help bring the conversation to life and can be placed before or after the spoken line.

Format:
{char1}: [expression] ...
{char2}: [expression] ...
(repeat)

Write the entire script in {script_language}. If {script_language} is Hinglish, use Latin script for all Hindi words and mix with English naturally, as in real Hinglish conversations. Do not use Devanagari script.
"""

def get_transliteration_prompt(chunk: str) -> str:
    """
    Generates the prompt for transliterating Hindi text to Hinglish.
    """
    return (
        "You are a strict transliteration engine. Your ONLY job is to convert every Hindi word in the following text from Devanagari script to Latin script (Hinglish). Do NOT summarize, translate, paraphrase, or add/remove any words, punctuation, or lines. Do NOT output any Hindi/Devanagari script or explanation. Output must be the same length and structure as the input, but with all Hindi words in Latin script. Output ONLY the transliterated text, nothing else. If you see any non-Hindi text, leave it unchanged. Here is the text (UTF-8 encoded):\n\n"
        f"{chunk}"
    )

def get_bark_narration_prompt(text_clean: str) -> str:
    """
    Generates the prompt for Bark TTS narration.
    """
    return text_clean  # Bark doesn't need a complex prompt, just the cleaned text.

def get_elevenlabs_narration_prompt(text_clean: str) -> str:
    """
    Generates the prompt for ElevenLabs TTS narration.
    """
    return text_clean  # ElevenLabs doesn't need a complex prompt, just the cleaned text. 