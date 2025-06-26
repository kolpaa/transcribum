from enum import StrEnum

class AudioExtensions(StrEnum):
    """Поддерживаемые аудиоформаты для транскрибации"""
    MP3 = 'mp3'
    WAV = 'wav'
    OGG = 'ogg'
    FLAC = 'flac'
    OPUS = 'opus'
    M4A = 'm4a'
    OGA = 'oga'

class VideoExtensions(StrEnum):
    """Видеоформаты (аудио будет извлечено)"""
    MP4 = 'mp4'
    AVI = 'avi'
    MOV = 'mov'
    WEBM = 'webm'

class ResultExtensions(StrEnum):
    PDF = 'pdf'
    DOCX = 'docx'
    
class LLMPrompts(StrEnum):
    MAKE_POST = "Напиши пост для социальной сети на основе этих данных"
    MAKE_SUMMARY = "Напиши краткое содержание на основе этих данных"
    MAKE_POST_SHORT = "p"
    MAKE_SUMMURY_SHORT = "s"