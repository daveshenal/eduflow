"""Audio generation utilities using Azure Speech SDK."""

import os
import re
import time
import uuid
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk

from app.adapters.azure_speech import speech_config


# Configuration
OUTPUT_DIR = Path("temp/audio_chunks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Request/Response Models
class TTSRequest(BaseModel):
    """Model for text-to-speech synthesis requests."""
    text: str
    voice: Optional[str] = "en-US-JennyNeural"
    speed: Optional[str] = "medium"  # x-slow, slow, medium, fast, x-fast
    pitch: Optional[str] = "medium"  # x-low, low, medium, high, x-high

# Helper function to create SSML
def create_ssml(text: str, voice: str, speed: str, pitch: str) -> str:
    """Create SSML markup for speech synthesis."""
    processed_text = re.sub(r'\.', '.<break time="300ms"/>', text)

    return f"""
    <speak version='1.0' xml:lang='en-US' xmlns:mstts='https://www.w3.org/2001/mstts'>
        <voice name='{voice}'>
            <prosody rate='{speed}' pitch='{pitch}'>
                {processed_text}
            </prosody>
        </voice>
    </speak>
    """

# Split long text into Azure-friendly chunks
def split_text_into_chunks(text: str, max_chars: int = 4000) -> list[str]:
    """
    Splits text into chunks under Azure's 5000 character limit.
    Tries to split on sentence endings.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += " " + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def synthesize_text(request: TTSRequest) -> dict:
    """Synthesize text to MP3 and return file info with retry logic."""
    if not request.text.strip():
        raise ValueError("Text cannot be empty")

    max_retries = 3
    base_delay = 1  # Base delay in seconds
    max_delay = 15  # Maximum delay in seconds

    for attempt in range(max_retries + 1):
        try:
            # Configure and create synthesizer
            speech_config.speech_synthesis_voice_name = request.voice
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, audio_config=None)
            ssml = create_ssml(request.text, request.voice,
                               request.speed, request.pitch)

            # Log attempt info for production monitoring
            logging.info(
                "TTS synthesis attempt %s/%s for text length: %s", attempt + 1, max_retries + 1, len(request.text))

            # Perform synthesis
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                file_id = str(uuid.uuid4())
                filename = f"{file_id}.mp3"
                file_path = OUTPUT_DIR / filename
                with open(file_path, "wb") as audio_file:
                    audio_file.write(result.audio_data)

                # Log success for monitoring
                if attempt > 0:
                    logging.info(
                        "TTS synthesis succeeded on attempt %s", attempt + 1)

                return {
                    'success': True,
                    'message': "Speech synthesized successfully",
                    'file_id': file_id,
                    'file_path': str(file_path),
                    'attempts': attempt + 1  # Track retry count for monitoring
                }

            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                error_msg = f"Speech synthesis canceled: {cancellation.reason}"
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    error_msg += f" - {cancellation.error_details}"

                # Check if this is a retryable error
                is_timeout = "timeout" in error_msg.lower()
                is_network_error = any(keyword in error_msg.lower() for keyword in
                                     ["network", "connection", "service unavailable", "server error"])

                if (is_timeout or is_network_error) and attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logging.warning(
                        "TTS synthesis failed (attempt %s): %s. Retrying in %ss...", attempt + 1, error_msg, delay)
                    time.sleep(delay)
                    continue  # Retry
                # Non-retryable error or max retries reached
                logging.error(
                    "TTS synthesis failed permanently after %s attempts: %s", attempt + 1, error_msg)
                raise Exception(error_msg)
            else:
                # Unexpected result - don't retry
                error_msg = f"Unexpected synthesis result: {result.reason}"
                logging.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            # Handle non-Azure SDK exceptions (file I/O, etc.)
            if attempt < max_retries and "timeout" in str(e).lower():
                delay = min(base_delay * (2 ** attempt), max_delay)
                logging.warning(
                    "TTS synthesis exception (attempt %s): %s. Retrying in %ss...", attempt + 1, str(e), delay)
                time.sleep(delay)
                continue
            logging.error("TTS synthesis failed permanently: %s", e)
            raise

    # This should never be reached, but just in case
    raise Exception("Maximum retry attempts exceeded")

def merge_mp3_files(file_paths: list[str], output_path: str):
    """Merge multiple MP3 files into one."""
    combined = AudioSegment.empty()
    for path in file_paths:
        audio = AudioSegment.from_mp3(path)
        combined += audio
    combined.export(output_path, format="mp3")
    return output_path

def generate_mp3_from_file(text_file_path: str, output_file_path: str, voice: str = "en-US-EmmaNeural", speed: str = "medium", pitch: str = "medium") -> str:
    """
    Main function to generate MP3 from text file.
    This function can be imported and used in your main script.
    
    Args:
        text_file_path: Path to the text file to convert
        output_file_path: Path where the final MP3 should be saved
        voice: Voice to use for synthesis
        speed: Speech speed
        pitch: Speech pitch
    
    Returns:
        str: Path to the generated MP3 file
    """
    # Load text
    with open(text_file_path, "r", encoding="utf-8") as file:
        text_content = file.read()

    # Split text into Azure-safe chunks
    chunks = split_text_into_chunks(text_content)
    mp3_files = []

    for i, chunk in enumerate(chunks, 1):
        request = TTSRequest(
            text=chunk,
            voice=voice,
            speed=speed,
            pitch=pitch
        )
        try:
            result = synthesize_text(request)
            mp3_files.append(result['file_path'])
            logging.info("Chunk %s synthesized: %s", i, result['file_path'])
        except Exception as e:
            logging.info("Error in chunk %s: %s", i, e)
            raise e

    # Merge all MP3s into one final file
    if mp3_files:
        merge_mp3_files(mp3_files, output_file_path)
        logging.info("\nAll chunks merged into: %s", output_file_path)

        # Clean up temporary chunk files
        for temp_file in mp3_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                logging.info(
                    f"Warning: Could not remove temp file {temp_file}: {e}")

        return output_file_path
    else:
        raise Exception("No MP3 files were generated")

# if __name__ == "__main__":
#     import time

#     # Path to the input text file
#     text_file = "temp/doc-1.txt"  # replace with file path
#     # Path to the output MP3
#     output_mp3 = "test.mp3"

#     # Voice settings
#     voice = "en-US-AndrewNeural"
#     speed = "medium"
#     pitch = "medium"

#     try:
#         start = time.perf_counter()
#         final_mp3 = generate_mp3_from_file(
#             text_file_path=text_file,
#             output_file_path=output_mp3,
#             voice=voice,
#             speed=speed,
#             pitch=pitch
#         )
#         elapsed = time.perf_counter() - start
#         print(f"Synthesis wall-clock: {elapsed:.1f}s")
#         logging.info(f"MP3 generated successfully: {final_mp3}")
#     except Exception as e:
#         logging.info(f"Error generating MP3: {e}")
