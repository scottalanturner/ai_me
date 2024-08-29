from io import BytesIO
from typing import IO
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import uuid

class TextToAudio():
    def __init__(self, api_key: str):
        self.api_key = api_key

        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY variable not set")
        
        self.client = ElevenLabs(api_key=api_key)


    def text_to_speech_stream(self, text: str, voice_id: str) -> IO[bytes]:
        """
        Converts text to speech and returns the audio data as a byte stream.

        This function invokes a text-to-speech conversion API with specified parameters, including
        voice ID and various voice settings, to generate speech from the provided text. Instead of
        saving the output to a file, it streams the audio data into a BytesIO object.

        Args:
            text (str): The text content to be converted into speech.

        Returns:
            IO[bytes]: A BytesIO stream containing the audio data.
        """
        # Perform the text-to-speech conversion
        response = self.client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        #webm_file_path = f"{uuid.uuid4()}.mp3"
        #with open(webm_file_path, "wb") as f:
        #    for chunk in response:
        #        if chunk:
        #            f.write(chunk)
            #response.stream_to_file(webm_file_path)
        
        #return webm_file_path
        #print("Streaming audio data...")

        # Create a BytesIO object to hold audio data
        audio_stream = BytesIO()

        # Write each chunk of audio data to the stream
        for chunk in response:
            if chunk:
                audio_stream.write(chunk)

        # Reset stream position to the beginning
        audio_stream.seek(0)

        # Return the stream for further use
        return audio_stream
