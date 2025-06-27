import os
import subprocess
import ffmpeg
import re
import shutil, random, string
from src.domain.constants import ResultExtensions
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from textwrap import wrap
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import logging, requests

from src.domain.interfaces import IFileService, ILinkService

class FileService(IFileService):

    @classmethod
    def delete_files(cls, *files: str) -> bool:
        all_deleted = True
        for file in files:
            if os.path.exists(file):
                os.remove(file)
                continue
            all_deleted = False
        return all_deleted
    
    @classmethod
    def delete_all_from_folders(cls, *folders: str) -> bool:
        success = True
        for folder in folders:
            if not os.path.isdir(folder):
                logging.warning(f"Папка не найдена: {folder}")
                success = False
                continue

            try:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        filepath = os.path.join(root, file)
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            logging.error(f"Не удалось удалить файл {filepath}: {e}")
                            success = False
            except Exception as e:
                logging.error(f"Ошибка при обработке папки {folder}: {e}")
                success = False

        return success


    @classmethod
    def covert_media_to_wav(cls, filepath):
        filename, ext = os.path.splitext(filepath)
        if ext != ".wav":
            process = subprocess.run(['ffmpeg', "-y", '-i', filepath, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', filename + ".wav"])
            if os.path.exists(filename + ".wav"):
                cls.delete_files(filepath)
                return filename + ".wav"
            return ""
        return filepath
    
    @classmethod
    def get_media_duration(cls, file_path):
        probe = ffmpeg.probe(file_path)
        stream = next((s for s in probe['streams'] if 'duration' in s), None)
        if stream:
            return int(float(stream['duration']))
        return None
    
    @classmethod
    def add_directory(cls, base_path, path):
        new_path = os.path.join(base_path, path)
        os.makedirs(new_path, exist_ok=True)
        return new_path

    @classmethod
    def _txt_to_pdf(cls, txt_file_path, pdf_file_path):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from textwrap import wrap
        import os

        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        FONT_PATH = os.path.join(CURRENT_DIR, "DejaVuSans.ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))

        page_width, page_height = A4
        margin = 40
        line_height = 14
        font_name = "DejaVu"  # ← используем правильный шрифт
        font_size = 10
        max_lines_per_page = int((page_height - 2 * margin) / line_height)

        c = canvas.Canvas(pdf_file_path, pagesize=A4)
        c.setFont(font_name, font_size)

        max_line_width = page_width - 2 * margin
        avg_char_width = c.stringWidth("M", font_name, font_size)
        max_chars_per_line = int(max_line_width / avg_char_width)

        with open(txt_file_path, "r", encoding="utf-8-sig") as file:
            lines = file.readlines()

        y = page_height - margin
        line_count = 0

        for line in lines:
            wrapped_lines = wrap(line.strip(), width=max_chars_per_line)

            for wrapped_line in wrapped_lines:
                if line_count >= max_lines_per_page:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = page_height - margin
                    line_count = 0

                c.drawString(margin, y, wrapped_line)
                y -= line_height
                line_count += 1

        c.save()


    @classmethod
    def _txt_to_docx(cls, txt_file_path, docx_file_path):
        doc = Document()
                
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            lines = txt_file.readlines()
                
        for line in lines:
            doc.add_paragraph(line.strip())
        doc.save(docx_file_path)

    @classmethod
    def convert_txt_to_ext(cls, txt_path, ext):
        result = f"{os.path.splitext(txt_path)[0]}.{ext}"
    
        converters = {
            ResultExtensions.DOCX: cls._txt_to_docx,
            ResultExtensions.PDF: cls._txt_to_pdf,
        }
        
        convert_func = converters.get(ext)
        if convert_func:
            convert_func(txt_path, result)
            return result
        return None

 
class LinkService(ILinkService):
    @classmethod
    def getDirectLinkFromMailCloudUrl(link):
        # link should look like 'https://cloud.mail.ru/public/XXX/YYYYYYYY'
        response = requests.get(link)
        page_content = response.text

        re_pattern = r'dispatcher.*?weblink_get.*?url":"(.*?)"'
        match = re.search(re_pattern , page_content)

        if match:
            url = match.group(1)
            # get /XXX/YYYYYYYY from source link
            parts = link.split('/')[-2:]
            # add XXX and YYYYYYYY to result link
            url = f'{url}/{parts[0]}/{parts[1]}'
            return url
        
        return None
    @classmethod
    def create_random_copy(cls, file_path):
        # Получаем директорию и имя исходного файла
        dir_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]  # Получаем расширение файла
        
        # Генерируем случайное имя (10 символов)
        random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        new_file_name = random_name + file_ext
        new_file_path = os.path.join(dir_path, new_file_name)
        
        # Копируем файл
        shutil.copy2(file_path, new_file_path)
        return new_file_path


    @classmethod
    def download_link(cls, link, download_dir="downloads"):
        os.makedirs(download_dir, exist_ok=True)

        output_template = os.path.join(download_dir, "%(title)s.%(ext)s")
        if "cloud.mail.ru" in link:
            link = cls.getDirectLinkFromMailCloudUrl(link)
            if not link:
                return None
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

    
    @classmethod
    def parse_links(cls, raw_links):
        link_pattern = link_pattern = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        all_links = re.findall(link_pattern, raw_links)
        clear_links = []
        for i in range(0, len(all_links)):
            clear_links.append(all_links[i][0])
        return clear_links
    

    
