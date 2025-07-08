import io
import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv # Dodaj ten import
import soundfile as sf
import numpy as np

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True # Potrzebne, aby bot widział treści komend tekstowych
intents.members = True       # Przydatne do niektórych informacji o użytkownikach
intents.voice_states = True  # Kluczowe! Pozwala botowi na interakcję z kanałami głosowymi

bot = commands.Bot(command_prefix='!', intents=intents)

voice_clients = {}
audio_buffers = {}
recording_in_progress = {}

@bot.event
async def on_ready():
    """Wywoływane, gdy bot jest gotowy i zalogowany do Discorda."""
    print(f'Zalogowano jako {bot.user.name} ({bot.user.id})') # type: ignore
    print('Bot jest gotowy do działania!')
    print('---')
    
@bot.command()
async def polacz(ctx):
    """
    Bot dołącza do kanału głosowego, na którym znajduje się użytkownik
    wywołujący komendę.
    """
    # Sprawdzamy, czy użytkownik jest na kanale głosowym.
    if not ctx.author.voice:
        await ctx.send("Musisz być na kanale głosowym, aby bot mógł do niego dołączyć.")
        return

    # Pobieramy kanał głosowy, na którym znajduje się użytkownik.
    channel = ctx.author.voice.channel

    # Sprawdzamy, czy bot jest już połączony z kanałem głosowym na tym serwerze.
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
        # Jeśli tak, informujemy użytkownika, że już jest połączony i do jakiego kanału.
        await ctx.send(f"Jestem już połączony z kanałem głosowym: **{voice_clients[ctx.guild.id].channel.name}**.")
        return

    # Próbujemy połączyć bota z kanałem głosowym.
    try:
        voice_client = await channel.connect()
        
        # Zapisujemy obiekt połączenia głosowego w naszym słowniku.
        voice_clients[ctx.guild.id] = voice_client
        audio_buffers[ctx.guild.id] = io.BytesIO() # Reset bufora audio dla nowego połączenia
        recording_in_progress[ctx.guild.id] = False # Reset flagi nagrywania
        await ctx.send(f"Dołączyłem do kanału głosowego: **{channel.name}**.")
    except asyncio.TimeoutError:
        # Obsługa błędu, jeśli połączenie trwa zbyt długo.
        await ctx.send("Nie udało się połączyć z kanałem głosowym (przekroczono limit czasu).")
    except discord.ClientException as e:
        # Obsługa innych błędów Discorda, np. brak uprawnień.
        await ctx.send(f"Błąd połączenia: {e}")
    except Exception as e:
        # Ogólna obsługa innych, nieprzewidzianych błędów.
        await ctx.send(f"Wystąpił nieoczekiwany błąd podczas łączenia: {e}")
        print(f"Nieoczekiwany błąd w komendzie !polacz: {e}")
        
# --- Komenda: Rozlącz z kanałem głosowym ---
@bot.command()
async def rozlacz(ctx):
    """
    Bot opuszcza kanał głosowy, jeśli jest połączony na danym serwerze.
    """
    # Sprawdzamy, czy bot jest połączony z kanałem głosowym na tym serwerze.
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
        if ctx.guild.id in audio_buffers:
            del audio_buffers[ctx.guild.id]
        if ctx.guild.id in recording_in_progress:
            del recording_in_progress[ctx.guild.id]
        # Odłączamy bota od kanału głosowego.
        await voice_clients[ctx.guild.id].disconnect()
        # Usuwamy połączenie ze słownika, aby zwolnić zasoby.
        del voice_clients[ctx.guild.id]
        await ctx.send("Opuściłem kanał głosowy.")
    else:
        # Informujemy, że bot nie jest połączony.
        await ctx.send("Nie jestem połączony z żadnym kanałem głosowym na tym serwerze.")
        
# --- Komenda: Prosty test połączenia ---
@bot.command()
async def ping(ctx):
    """Prosta komenda testowa, aby sprawdzić, czy bot odpowiada."""
    await ctx.send('Pong!')

# --- Uruchomienie Bota ---
if TOKEN:
    # bot.run() blokuje wykonanie, więc musi być ostatnim wywołaniem
    bot.run(TOKEN)
else:
    print("Błąd: Token bota nie został znaleziony w zmiennej środowiskowej DISCORD_BOT_TOKEN.")
    print("Upewnij się, że ustawiłeś zmienną środowiskową przed uruchomieniem bota, np.:")
    print("export DISCORD_BOT_TOKEN='TWÓJ_TOKEN_BOTA'")
    
@bot.command()
async def nagrywaj(ctx):
    """
    Rozpoczyna nagrywanie rozmowy na kanale głosowym, do którego bot jest podłączony.
    Wymaga zgody wszystkich uczestników!
    """
    if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
        await ctx.send("Nie jestem połączony z żadnym kanałem głosowym. Użyj komendy `!polacz`.")
        return

    if recording_in_progress[ctx.guild.id]:
        await ctx.send("Nagrywanie jest już w toku!")
        return

    # *** WAŻNE: MECHANIZM ZGODY ***
    # Pamiętaj, aby ZAWSZE uzyskać JAWNĄ ZGODĘ wszystkich uczestników rozmowy
    # przed rozpoczęciem nagrywania. Ten bot jest na użytek prywatny, ale
    # zasady prywatności i RODO są kluczowe.
    await ctx.send("Rozpoczynam nagrywanie. **Pamiętaj, aby uzyskać zgodę wszystkich uczestników.**\n"
                   "Użyj `!stop_nagrywania`, aby zakończyć nagrywanie.")

    voice_client = voice_clients[ctx.guild.id]
    recording_in_progress[ctx.guild.id] = True
    audio_buffers[ctx.guild.id] = io.BytesIO() # Upewnij się, że bufor jest pusty na początek nowego nagrania

    # Funkcja zwrotna (callback) dla danych audio
    def audio_callback(sink, error):
        if error:
            print(f"Błąd w callbacku audio: {error}")
            return

        # sink.audio_data zawiera dane od każdego użytkownika (id_użytkownika: opus_packet)
        # Na tym etapie zbieramy WSZYSTKIE audio w jeden strumień, bez rozróżniania mówców.
        for user_id, audio_opus_packet in sink.audio_data.items():
            try:
                # Dekodujemy pakiet Opus do surowego PCM (Pulse Code Modulation)
                # pcm to 16-bitowe inty, 48kHz
                pcm_data = audio_opus_packet.pcm

                # Konwertujemy pcm_data na numpy array float32, zakres [-1.0, 1.0]
                # Taki format jest preferowany przez soundfile i Whisper.
                audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

                # soundfile.write może zapisać numpy array do obiektu plikowego (takiego jak BytesIO)
                # Musimy otworzyć BytesIO w trybie binarnym ('wb') i jawnie określić format i próbkowanie.
                # Niestety, soundfile nie obsługuje trybu "append" do BytesIO wprost,
                # więc musimy zbierać dane w pamięci i potem zapisać lub użyć sztuczki.

                # Najprostsze rozwiązanie dla testu: po prostu zapisujemy do bufora.
                # UWAGA: Dla bardzo długich nagrań to może zużywać dużo RAM.
                # W przyszłości: bardziej zaawansowane buforowanie lub zapis do pliku tymczasowego.

                # Aby dopisać do BytesIO, musimy "przewinąć" do końca i dopisać
                current_pos = audio_buffers[ctx.guild.id].tell()
                audio_buffers[ctx.guild.id].seek(current_pos)
                # sf.write do BytesIO musi być wywołane raz z pełnymi danymi, lub BytesIO musi być "file-like object" obsługujący seek/read/write
                # Bardziej niezawodne podejście to zbieranie raw pcm_data do listy i sklejenie ich na końcu.

                # Na razie, dla uproszczenia (i ryzyka RAM dla długich nagrań):
                # zbieramy surowe pcm_data do tymczasowej listy
                if not hasattr(audio_buffers[ctx.guild.id], '_pcm_chunks'):
                    audio_buffers[ctx.guild.id]._pcm_chunks = []
                audio_buffers[ctx.guild.id]._pcm_chunks.append(pcm_data)

            except Exception as e:
                print(f"Błąd podczas przetwarzania pakietu audio: {e}")

    # Rozpocznij nasłuchiwanie - używamy WaveSink, który zbiera audio od wszystkich i konwertuje do WAV.
    # To znacznie upraszcza dalsze przetwarzanie, bo dostajemy gotowe dane WAV.
    # discord.sinks.PCMVolumeTransformer jest często używany, ale dla WaveSink nie jest wymagany
    voice_client.listen(discord.sinks.WaveSink(callback=audio_callback)) # type: ignore
    # Tutaj przekazujemy nasz audio_callback do WaveSink, który będzie go wywoływał z danymi audio.


@bot.command()
async def stop_nagrywania(ctx):
    """
    Zatrzymuje nagrywanie i informuje o jego zakończeniu.
    Później tutaj nastąpi transkrypcja.
    """
    if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
        await ctx.send("Nie jestem połączony z żadnym kanałem głosowym.")
        return

    if not recording_in_progress[ctx.guild.id]:
        await ctx.send("Nagrywanie nie jest w toku.")
        return

    voice_client = voice_clients[ctx.guild.id]
    voice_client.stop_listening() # To zatrzymuje nasłuchiwanie

    recording_in_progress[ctx.guild.id] = False # Ustawienie flagi na False

    # Odbierz zebrane dane audio z WaveSink
    # WaveSink przechowuje je w sink.audio_data
    # Niestety, musimy poczekać aż listen się zakończy, aby mieć dostęp do pełnych danych
    # Inaczej musielibyśmy zbierać je w osobnym wątku/funkcji asynchronicznej.
    # Dla prostoty na razie po prostu poinformujemy.

    # UWAGA: Ten fragment kodu jest uproszczony. Pełne dane z WaveSink zbierane są
    # po zakończeniu nasłuchiwania. W callbacku audio_callback zbieramy tylko
    # poszczególne pakiety. Aby je złożyć w całość, potrzebna jest dodatkowa logika.
    # W kolejnym kroku pokażę, jak zebrać je poprawnie po stop_listening().

    await ctx.send("Nagrywanie zatrzymane. Dane audio zostały zebrane. (W przyszłości nastąpi transkrypcja)")

# ... (istniejące komendy ping i hello)

# ... (istniejący fragment z uruchomieniem bota)
