# Test for Hindi to Hinglish transliteration (moved from root)
import requests
import json

def convert_hindi_to_hinglish_ollama(hindi_text, model="gemma3:4b"):
    prompt = (
        "Convert this Hindi sentence to Hinglish (write in Latin script, keep the meaning and style). Only output the Hinglish sentence, nothing else. Transliterate all Hindi words to Latin script, do not leave any Devanagari or Hindi script in the output.\n\n"
        f"{hindi_text}"
    )
    OLLAMA_URL = "http://localhost:11434/api/generate"
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            print(f"Ollama API error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception during Ollama call: {e}")
        return None

def main():
    hindi_text = "और वो जीनियस का इस्तेमाल नहीं किया उसननंबर टू मुझे कमेंट्स में बताओ इस एपिसोड में आपको क्या अच्छा लगा और क्या गंदा लगा ताकि हम वो मिस्टेक्स रिपीट ना कर पाए एंड कौन से ऐसे गेस्ट हैं जो आप देखना चाहते हो वापस हमारे पडकास्ट पे ताकि हम उन्हें लेके आए और आपको ज्यादा से ज्यादा वैल्यू दे पाए"
    hinglish_text = convert_hindi_to_hinglish_ollama(hindi_text)
    print("Hindi Text:", hindi_text)
    print("Converted Hinglish Text:", hinglish_text)

if __name__ == "__main__":
    main()
