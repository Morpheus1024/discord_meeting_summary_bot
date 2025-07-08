from transformers import pipeline
import torch

class Text2SpeechModel:
    def __init__(self, device="cuda" if torch.cuda.is_available() else "cpu"):
        self.asr = pipeline(
            "automatic-speech-recognition",
            model="jonatasgrosman/wav2vec2-large-xlsr-53-polish",
            device=device
        )
    
    def transcribe(self, audio_path, language="pol"):
        result = self.asr(
            audio_path,
            chunk_length_s=30,
            generate_kwargs={"language": language}
        )
        return result["text"], result