import azure.cognitiveservices.speech as speechsdk
from config.settings import settings

# Configuration
SPEECH_KEY = settings.AZURE_SPEECH_KEY
SERVICE_REGION = settings.AZURE_SPEECH_REGION

# Initialize Azure Speech Config
speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SERVICE_REGION)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
)