from pydub import AudioSegment
import os

# Function to split mp3
def split_mp3(file_path, max_size_mb):
    audio = AudioSegment.from_mp3(file_path)
    file_size = len(audio)  # in milliseconds
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Calculate approximate duration to fit the size
    duration_per_split = int((max_size_bytes / os.path.getsize(file_path)) * file_size)
    
    # Split the audio and save the parts
    for i in range(0, len(audio), duration_per_split):
        split_audio = audio[i:i + duration_per_split]
        split_audio.export(f"part_{i // duration_per_split}.mp3", format="mp3")
        print(f"Exported: part_{i // duration_per_split}.mp3")

# Example usage:
#split_mp3("/Users/sturner/Downloads/ViewfromtheTop.mp3", 9)  # Split into 10MB parts

split_mp3("/Users/sturner/Downloads/AIME/bobby_shaw/audio/re_podcast.mp3", 9)  # 10MB parts
