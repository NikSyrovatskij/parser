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
            KeyboardButton(text="📱 Настройка телефона"),
            KeyboardButton(text="🦊 Sing-Box → VLESS"),
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

    # Кнопки быстрого подключения: Копирование и QR-код
    action_row = []
    if len(link) <= 1024:
        action_row.append(
            InlineKeyboardButton(
                text="📋 Скопировать",
                copy_text=CopyTextButton(text=link),
            )
        )
    action_row.append(
        InlineKeyboardButton(
            text="📷 QR-код",
            callback_data=f"qr:{srv_id}:{page}",
        )
    )
    rows.append(action_row)

    # Кнопки экспорта этого сервера в Clash и Sing-Box
    rows.append(
        [
            InlineKeyboardButton(
                text="📦 В Clash",
                callback_data=f"exp_clash:{srv_id}",
            ),
            InlineKeyboardButton(
                text="🦊 В Sing-Box",
                callback_data=f"exp_sb:{srv_id}",
            ),
        ]
    )

    # Кнопка подсказки по настройке на телефоне
    rows.append(
        [
            InlineKeyboardButton(
                text="📱 Как настроить на телефоне",
                callback_data=f"phone_setup_from_srv:{srv_id}:{page}",
            )
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


# Клавиатура под отправленным QR-кодом
def get_qr_detail_keyboard(link: str) -> InlineKeyboardMarkup:
    rows = []
    if len(link) <= 1024:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📋 Скопировать ссылку",
                    copy_text=CopyTextButton(text=link),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 Скрыть QR-код",
                callback_data="delete_msg",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Главное меню мастера настройки телефона
def get_phone_setup_menu_keyboard(back_srv: str = "none") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🍏 iPhone (iOS)", callback_data=f"phone_os:ios:{back_srv}"),
            InlineKeyboardButton(text="🤖 Android", callback_data=f"phone_os:android:{back_srv}"),
        ],
        [
            InlineKeyboardButton(
                text="🔗 Подключение по ссылке (всей подписки)",
                callback_data=f"phone_sub_info:{back_srv}",
            )
        ],
    ]
    if back_srv != "none":
        # back_srv в формате "srv_id:page"
        parts = back_srv.split(":")
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к серверу",
                    callback_data=f"srv:{parts[0]}:{parts[1]}",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Закрыть",
                    callback_data="delete_msg",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Выбор приложений для конкретной ОС
def get_phone_os_keyboard(os_name: str, back_srv: str = "none") -> InlineKeyboardMarkup:
    rows = []
    if os_name == "ios":
        rows.append(
            [
                InlineKeyboardButton(
                    text="1️⃣ Happ Proxy (Рекомендуется)",
                    callback_data=f"phone_app:ios_happ:{back_srv}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="2️⃣ Streisand",
                    callback_data=f"phone_app:ios_streisand:{back_srv}",
                ),
                InlineKeyboardButton(
                    text="3️⃣ V2Box / FoXray",
                    callback_data=f"phone_app:ios_v2box:{back_srv}",
                ),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="1️⃣ Happ Proxy (Рекомендуется)",
                    callback_data=f"phone_app:and_happ:{back_srv}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="2️⃣ v2rayNG",
                    callback_data=f"phone_app:and_v2rayng:{back_srv}",
                ),
                InlineKeyboardButton(
                    text="3️⃣ Hiddify / NekoBox",
                    callback_data=f"phone_app:and_hiddify:{back_srv}",
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к выбору ОС",
                callback_data=f"phone_menu:{back_srv}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Кнопка возврата из карточки приложения
def get_phone_app_back_keyboard(os_name: str, back_srv: str = "none") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку приложений",
                    callback_data=f"phone_os:{os_name}:{back_srv}",
                )
            ]
        ]
    )

