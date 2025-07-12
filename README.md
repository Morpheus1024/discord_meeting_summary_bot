# Discord Meeting Summary Bot

This project is a Discord bot that allows you to record voice conversations on a server, transcribe the recording to text, and automatically generate a summary of the conversation in Polish.

## Features

- **Voice channel recording** – the bot joins a voice channel and can record the conversation after obtaining participants' consent.
- **Audio-to-text transcription** – uses the `wav2vec2-large-xlsr-53-polish` model for automatic speech recognition from audio files (e.g., `.flac`).
- **Text summarization** – generates concise summaries of long texts (e.g., conversation transcripts) using the `microsoft/mbart-large-cc25` model.
- **Discord integration** – supports text and voice commands, joining and leaving channels, starting and stopping recording.

## Requirements

- Python 3.8+
- CUDA-enabled GPU (optional, for faster model inference)
- All packages from `requirements.txt` installed

'''
pip install -r requirements.txt
source .venv/bin/activate
'''

## Installation

1. Clone the repository and navigate to the project directory.
2. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your Discord bot token:
   ```
   DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN
   ```

## Usage

To run the bot:
```
python lib/bot.py
```

To test transcription or summarization on local files:
```
python test.py
```

## Example Discord Commands

- `!polacz` – bot joins your voice channel
- `!rozlacz` – bot leaves the voice channel
- `!nagrywaj` – starts recording the conversation
- `!stop_nagrywania` – stops recording and saves the audio data
- `!ping` – checks if the bot is responsive

## Files

- `lib/bot.py` – main Discord bot file
- `lib/text2speachmodel.py` – speech-to-text transcription
- `lib/text_summary_model.py` – text summarization

## Notes

- Always obtain explicit consent from all participants before recording (GDPR!).
- The models may require downloading large files on first run.
- The project is under development – some features may need refinement.

---
