import subprocess
import re

def download_link(link):

        output_template = "%(title)s.%(ext)s"

        command = ["yt-dlp", link]
        command.extend([
            "-x", "--audio-format", "wav", 
            "--cookies-from-browser", "firefox",
            "--extractor-args", "youtube:player_client=default,-web_creator",
            "--force-overwrites",
            "-o", output_template
        ])
        # command.extend(["--restrict-filenames"])


        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print("Download error:", result.stderr)
            return None

        match = re.search(r'\[ExtractAudio\] Destination: (.+\.wav)', result.stdout)
        if match:
            file_path = match.group(1)
            return file_path

        print("Файл не найден в выводе yt-dlp")
        return None

download_link("https://www.youtube.com/watch?v=ctmy_6TXr5w")