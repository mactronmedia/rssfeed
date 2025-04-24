from langdetect import detect, DetectorFactory

# Ensuring consistent results
DetectorFactory.seed = 0

def detect_language(text: str) -> str:
    try:
        # Detecting language
        language = detect(text)
        return language
    except Exception as e:
        print(f"Error detecting language: {e}")
        return 'unknown'

# Example texts
texts = [
    "Hello, how are you?",
    "Hola, ¿cómo estás?",
    "Bonjour, comment ça va?",
    "Guten Tag, wie geht's?",
    "Ciao, come stai?",
    "Привет, как дела?",
    'Janša po oprostilni sodbi: Naš boj se šele začenja'
]

for text in texts:
    detected_language = detect_language(text)
    print(f"Text: '{text}' -> Detected Language: {detected_language}")
