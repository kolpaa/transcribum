import subprocess
import os

from src.domain.interfaces import ITranscriber


class WhisperTranscriber(ITranscriber):
    def __init__(self, settings: dict[str, str]):
        self.settings = settings
        self.directory = self.settings['transcripts_dir']

    def set_transcrib_path(self, path):
        self.directory = path

    def transcribe(self, file_path):

        try:
            subprocess.run(["python", "src/infrastructure/transcriber/whisper-diarization/diarize.py", 
                            "-a", file_path, 
                            "--no-stem", 
                            "--whisper-model", self.settings['model'], 
                            "--device", self.settings['device'],
                            "--output-path", self.directory])
            
            filename= f"{os.path.splitext(os.path.basename(file_path))[0]}.txt"
            path = os.path.join(self.directory, filename)

        except Exception as e:
            print(e)
            return None
        
        return path