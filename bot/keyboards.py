from math import ceil
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
)

# Главное меню бота
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📥 Вставить ссылку подписки")],
        [
            KeyboardButton(text="📋 Посмотреть ссылки"),
            KeyboardButton(text="🔄 Обновить ссылки"),
        ],
        [
            KeyboardButton(text="🦊 Конвертер Sing-Box → VLESS"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите действие в меню...",
    )


# Кнопка отмены ввода ссылки подписки
def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_input")]
        ]
    )


# Кнопка отмены загрузки Sing-Box
def get_cancel_singbox_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_singbox")]
        ]
    )


def get_single_link_keyboard(link: str) -> InlineKeyboardMarkup:
    rows = []
    if len(link) <= 1024:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📋 Скопировать в буфер",
                    copy_text=CopyTextButton(text=link),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Инлайн-клавиатура со списком серверов и пагинацией
def get_servers_inline_keyboard(
    servers: list[dict], page: int = 0, per_page: int = 6
) -> InlineKeyboardMarkup:
    total_servers = len(servers)
    total_pages = max(1, ceil(total_servers / per_page))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_servers)
    page_servers = servers[start_idx:end_idx]

    keyboard_rows = []

    # Кнопки каждого сервера
    for srv in page_servers:
        # Обрезаем слишком длинные названия, чтобы умещались в кнопку
        title = srv["title"]
        if len(title) > 38:
            title = title[:35] + "..."
        
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"🌐 {title}",
                    callback_data=f"srv:{srv['id']}:{page}",
                )
            ]
        )

    # Строка навигации пагинации
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page - 1}")
        )
    
    if total_pages > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}/{total_pages}",
                callback_data="noop",
            )
        )
    
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page:{page + 1}")
        )

    if nav_row:
        keyboard_rows.append(nav_row)

    # Кнопки выгрузки всех серверов
    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="📦 Все в Clash (.yaml)", callback_data="dl_clash_all"
            ),
            InlineKeyboardButton(
                text="🦊 Все в Sing-Box (.json)", callback_data="dl_sb_all"
            ),
        ]
    )
    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="📁 Все ссылки (.txt)", callback_data="download_all"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


# Инлайн-клавиатура для конкретного выбранного сервера
def get_server_detail_keyboard(server: dict, page: int) -> InlineKeyboardMarkup:
    rows = []
    link = server["link"]
    srv_id = server["id"]

    # В Telegram Bot API CopyTextButton поддерживает текст до 1024 символов
    if len(link) <= 1024:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📋 Скопировать в буфер",
                    copy_text=CopyTextButton(text=link),
                )
            ]
        )

    # Кнопки экспорта этого сервера в Clash и Sing-Box
    rows.append(
        [
            InlineKeyboardButton(
                text="📦 Экспорт в Clash",
                callback_data=f"exp_clash:{srv_id}",
            ),
            InlineKeyboardButton(
                text="🦊 Экспорт в Sing-Box",
                callback_data=f"exp_sb:{srv_id}",
            ),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку",
                callback_data=f"page:{page}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)

