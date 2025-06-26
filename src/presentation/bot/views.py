from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.domain.constants import ResultExtensions, LLMPrompts

from aiogram.filters.callback_data import CallbackData

class GPTCallback(CallbackData, prefix="gpt"):
        file_path: str
        prompt: str

INITIAL_SELECTION = {
    ResultExtensions.DOCX: False,
    ResultExtensions.PDF : False,
    LLMPrompts.MAKE_POST: False,
    LLMPrompts.MAKE_SUMMARY: False
    }

OPTIONS = {
    ResultExtensions.DOCX: "📝 DOCX",
    ResultExtensions.PDF : "📄 PDF",
    LLMPrompts.MAKE_POST: "✂️ Короткий пост",
    LLMPrompts.MAKE_SUMMARY: "📋 Саммари"
    }

CONFIRM_BUTTON = "confirm_selection"


class TranscibumViews():
    
    @staticmethod
    def file_processing_error_message(error) -> str:
        return "Ошибка при обработке файла: {error}"
    
    @staticmethod
    def file_format_error() -> str:
        return "Неподдерживаемый формат файла"
    
    @staticmethod
    def top_up_balance_keyboard() -> str:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="Купить минуты", callback_data="top_up")]
        ])
        return keyboard

    @staticmethod
    def support() -> str:
        return """По всем вопросам и  предложениям обращайтесь:  
👉 @trjrjj  

Отвечаем быстро!  """

    @staticmethod
    def top_up_balance_message() -> str:
        return "Пополните баланс"
    
    @staticmethod
    def started_downloading() -> str:
        return "Загружаю файл..."
    
    @staticmethod
    def started_transcrib(filename) -> str:
        return f"Начинаю транскрибацию {filename}"
    
    @staticmethod
    def downloading_error() -> str:
        return "Ошибка при загрузке файла"

    @staticmethod
    def get_gpt_button(file_path, prompt) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
                    text="Улучшить в YandexGPT", 
                    callback_data=GPTCallback(file_path=file_path, prompt=prompt)
                    )
        return builder.as_markup()

    @staticmethod
    def get_options_keyboard(selection: dict) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.max_width = 2
        for key, label in OPTIONS.items():
            selected = selection.get(key, False)
            symbol = "✅" if selected else "❌"
            callback_data = f"toggle:{key.name}:{int(selected)}"
            builder.add(InlineKeyboardButton(text=f"{symbol} {label}", callback_data=callback_data))

        builder.row(InlineKeyboardButton(text="🔒 Подтвердить", callback_data=CONFIRM_BUTTON))
        return builder.as_markup()
    
    @staticmethod
    def bot_update():
        return """Новое обновление бота 🎉

✅ Поддержка формата .m4a

✅ Обработка больших файлов — даже в несколько гигабайт

✅ Уведомления о начале загрузки и транскрибации, чтобы вы всегда знали, на каком этапе ваш файл"""

    @staticmethod
    def get_greeting():
        return """Привет! Я — Транскрибум 🤖
Преобразую аудио и видео в текст за пару минут.

Загрузите файл одним из способов:

🔗 Отправьте ссылку на видео или аудио (YouTube, Google Drive и др.).

📎 Прикрепите файл до — подойдёт любой формат.

После обработки вы получите:

📝 Текстовую расшифровку в формате PDF, DOCX и TXT.
📌 Дополнительно можно:
— составить саммари,
— подготовить пост для соцсетей.

Начните с отправки файла или ссылки — остальное сделаю я!
transcribum.ru"""