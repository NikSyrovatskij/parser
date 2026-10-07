import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, BufferedInputFile
import html

from .database import Database
from .parser import fetch_and_parse_subscription, clean_subscription_url
from .keyboards import (
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_servers_inline_keyboard,
    get_server_detail_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()


class SubscriptionState(StatesGroup):
    waiting_for_url = State()


def get_db(message: Message) -> Database:
    return message.bot.db


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "👋 <b>Добро пожаловать в Happ Subscription Converter Bot!</b>\n\n"
        "Этот бот конвертирует подписки Happ Proxy в готовые ссылки <b>VLESS / Hysteria2</b> "
        "для приложений V2RayN, V2RayA, Streisand, v2rayNG, Hiddify, NekoBox и других.\n\n"
        "📌 <b>Возможности:</b>\n"
        "• <b>📥 Вставить ссылку подписки</b> — спарсить подписку и сохранить\n"
        "• <b>📋 Посмотреть ссылки</b> — открыть список серверов и скопировать в 1 клик\n"
        "• <b>🔄 Обновить ссылки</b> — повторно загрузить актуальные серверы\n\n"
        "Выберите действие в меню ниже 👇"
    )
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Справка по использованию:</b>\n\n"
        "1. Нажмите <b>«📥 Вставить ссылку подписки»</b> и отправьте ссылку вида <code>https://...</code> или <code>happ://add/...</code>\n"
        "2. Бот автоматически эмулирует клиент, снимет шифрование и выдаст список серверов с кнопками.\n"
        "3. Нажмите на любой сервер, чтобы скопировать ссылку VLESS/Hysteria.\n"
        "4. Чтобы получить все серверы разом, используйте кнопку <b>«📁 Скачать все ссылки (.txt)»</b> под списком.\n\n"
        "Команды:\n"
        "/start — Главное меню\n"
        "/subscribe — Вставить ссылку\n"
        "/servers — Посмотреть серверы\n"
        "/refresh — Обновить подписку"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "📥 Вставить ссылку подписки")
@router.message(Command("subscribe"))
async def prompt_subscribe(message: Message, state: FSMContext):
    await state.set_state(SubscriptionState.waiting_for_url)
    text = (
        "🔗 <b>Отправьте вашу ссылку на подписку:</b>\n\n"
        "Поддерживаются форматы:\n"
        "• <code>https://sub.domain.com/...</code>\n"
        "• <code>happ://add/https://...</code>\n\n"
        "<i>Отправьте ссылку в чат сообщением или нажмите «Отмена»:</i>"
    )
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "cancel_input")
async def callback_cancel_input(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Ввод ссылки отменён.")
    await callback.answer()


@router.message(SubscriptionState.waiting_for_url)
async def process_subscription_url(message: Message, state: FSMContext):
    raw_url = message.text.strip()
    try:
        cleaned_url = clean_subscription_url(raw_url)
    except ValueError as e:
        await message.answer(f"❌ {e}\nПожалуйста, отправьте корректную ссылку:")
        return

    status_msg = await message.answer("⏳ <i>Подключаюсь к серверу и парсю подписку...</i>", parse_mode="HTML")

    try:
        servers, raw_content = await fetch_and_parse_subscription(cleaned_url)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Ошибка при загрузке:</b>\n{html.escape(str(e))}", parse_mode="HTML")
        return

    # Сохраняем в базу данных
    db: Database = message.bot.db
    await db.save_user_subscription(
        user_id=message.from_user.id,
        subscription_url=cleaned_url,
        servers=servers,
        raw_content=raw_content,
    )
    await state.clear()

    await status_msg.delete()
    success_text = (
        f"✅ <b>Подписка успешно загружена!</b>\n"
        f"📡 Найдено серверов: <b>{len(servers)}</b>\n\n"
        "👇 <b>Выберите сервер из списка, чтобы скопировать ссылку:</b>"
    )
    await message.answer(
        success_text,
        reply_markup=get_servers_inline_keyboard(servers, page=0),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Посмотреть ссылки")
@router.message(Command("servers"))
async def show_servers(message: Message):
    db: Database = message.bot.db
    user_data = await db.get_user_subscription(message.from_user.id)

    if not user_data or not user_data.get("servers"):
        await message.answer(
            "⚠️ <b>У вас ещё нет сохранённой подписки.</b>\n\n"
            "Нажмите <b>«📥 Вставить ссылку подписки»</b>, чтобы добавить её.",
            parse_mode="HTML",
        )
        return

    servers = user_data["servers"]
    text = (
        f"📋 <b>Ваши серверы (всего {len(servers)}):</b>\n\n"
        "👇 Нажмите на кнопку с сервером, чтобы скопировать ссылку:"
    )
    await message.answer(
        text,
        reply_markup=get_servers_inline_keyboard(servers, page=0),
        parse_mode="HTML",
    )


@router.message(F.text == "🔄 Обновить ссылки")
@router.message(Command("refresh"))
async def refresh_servers(message: Message):
    db: Database = message.bot.db
    user_data = await db.get_user_subscription(message.from_user.id)

    if not user_data or not user_data.get("subscription_url"):
        await message.answer(
            "⚠️ <b>У вас ещё нет сохранённой подписки.</b>\n\n"
            "Сначала нажмите <b>«📥 Вставить ссылку подписки»</b>.",
            parse_mode="HTML",
        )
        return

    sub_url = user_data["subscription_url"]
    status_msg = await message.answer("⏳ <i>Обновляю подписку от провайдера...</i>", parse_mode="HTML")

    try:
        servers, raw_content = await fetch_and_parse_subscription(sub_url)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Ошибка при обновлении:</b>\n{html.escape(str(e))}", parse_mode="HTML")
        return

    await db.save_user_subscription(
        user_id=message.from_user.id,
        subscription_url=sub_url,
        servers=servers,
        raw_content=raw_content,
    )

    await status_msg.delete()
    text = (
        f"🔄 <b>Подписка успешно обновлена!</b>\n"
        f"📡 Доступно серверов: <b>{len(servers)}</b>\n\n"
        "👇 Выберите сервер, чтобы скопировать ссылку:"
    )
    await message.answer(
        text,
        reply_markup=get_servers_inline_keyboard(servers, page=0),
        parse_mode="HTML",
    )


# Перелистывание страниц серверов
@router.callback_query(F.data.startswith("page:"))
async def callback_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)

    if not user_data:
        await callback.answer("Подписка не найдена. Добавьте её заново.", show_alert=True)
        return

    servers = user_data["servers"]
    text = (
        f"📋 <b>Ваши серверы (всего {len(servers)}):</b>\n\n"
        "👇 Нажмите на кнопку с сервером, чтобы скопировать ссылку:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_servers_inline_keyboard(servers, page=page),
        parse_mode="HTML",
    )
    await callback.answer()


# Просмотр конкретного сервера для копирования
@router.callback_query(F.data.startswith("srv:"))
async def callback_server_detail(callback: CallbackQuery):
    parts = callback.data.split(":")
    srv_id = int(parts[1])
    page = int(parts[2])

    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)

    if not user_data:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    servers = user_data["servers"]
    target_srv = next((s for s in servers if s["id"] == srv_id), None)
    if not target_srv:
        await callback.answer("Сервер не найден.", show_alert=True)
        return

    title_safe = html.escape(target_srv["title"])
    proto_safe = html.escape(target_srv["proto"].upper())
    link_safe = html.escape(target_srv["link"])

    detail_text = (
        f"📡 <b>Сервер:</b> {title_safe}\n"
        f"⚙️ <b>Протокол:</b> <code>{proto_safe}</code>\n\n"
        f"👇 <b>Нажмите на блок ниже для копирования ссылки:</b>\n"
        f"<code>{link_safe}</code>"
    )

    await callback.message.edit_text(
        detail_text,
        reply_markup=get_server_detail_keyboard(target_srv, page=page),
        parse_mode="HTML",
    )
    await callback.answer()


# Скачивание файла со всеми ссылками
@router.callback_query(F.data == "download_all")
async def callback_download_all(callback: CallbackQuery):
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)

    if not user_data or not user_data.get("raw_content"):
        await callback.answer("Нет данных для скачивания.", show_alert=True)
        return

    file_content = user_data["raw_content"].encode("utf-8")
    document = BufferedInputFile(file_content, filename="vless_links.txt")

    await callback.message.answer_document(
        document=document,
        caption="📁 <b>Все ваши конфигурации серверов (.txt)</b>\nФайл можно импортировать в клиенты V2RayN, v2rayNG, Streisand и др.",
        parse_mode="HTML",
    )
    await callback.answer()


from .converters import generate_clash_yaml, generate_singbox_json


# Экспорт конкретного сервера в Clash (YAML)
@router.callback_query(F.data.startswith("exp_clash:"))
async def callback_export_clash_single(callback: CallbackQuery):
    srv_id = int(callback.data.split(":")[1])
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)
    if not user_data:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    target_srv = next((s for s in user_data["servers"] if s["id"] == srv_id), None)
    if not target_srv:
        await callback.answer("Сервер не найден.", show_alert=True)
        return

    yaml_content = generate_clash_yaml([target_srv])
    if not yaml_content:
        await callback.answer("Не удалось сконвертировать в Clash.", show_alert=True)
        return

    doc = BufferedInputFile(yaml_content.encode("utf-8"), filename=f"clash_server_{srv_id + 1}.yaml")
    caption = f"📦 <b>Конфигурация Clash Meta / Mihomo (YAML)</b>\nСервер: <code>{html.escape(target_srv['title'])}</code>"
    await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")
    await callback.answer()


# Экспорт конкретного сервера в Sing-Box (JSON)
@router.callback_query(F.data.startswith("exp_sb:"))
async def callback_export_singbox_single(callback: CallbackQuery):
    srv_id = int(callback.data.split(":")[1])
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)
    if not user_data:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    target_srv = next((s for s in user_data["servers"] if s["id"] == srv_id), None)
    if not target_srv:
        await callback.answer("Сервер не найден.", show_alert=True)
        return

    json_content = generate_singbox_json([target_srv])
    if not json_content:
        await callback.answer("Не удалось сконвертировать в Sing-Box.", show_alert=True)
        return

    doc = BufferedInputFile(json_content.encode("utf-8"), filename=f"singbox_server_{srv_id + 1}.json")
    caption = f"🦊 <b>Конфигурация Sing-Box (JSON)</b>\nСервер: <code>{html.escape(target_srv['title'])}</code>"
    await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")
    await callback.answer()


# Экспорт всех серверов в Clash (YAML)
@router.callback_query(F.data == "dl_clash_all")
async def callback_dl_clash_all(callback: CallbackQuery):
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)
    if not user_data or not user_data.get("servers"):
        await callback.answer("Нет серверов для экспорта.", show_alert=True)
        return

    yaml_content = generate_clash_yaml(user_data["servers"])
    doc = BufferedInputFile(yaml_content.encode("utf-8"), filename="clash_config.yaml")
    await callback.message.answer_document(
        document=doc,
        caption="📦 <b>Полный профиль Clash Meta / Mihomo (YAML)</b>\nСодержит все ваши серверы.",
        parse_mode="HTML",
    )
    await callback.answer()


# Экспорт всех серверов в Sing-Box (JSON)
@router.callback_query(F.data == "dl_sb_all")
async def callback_dl_sb_all(callback: CallbackQuery):
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)
    if not user_data or not user_data.get("servers"):
        await callback.answer("Нет серверов для экспорта.", show_alert=True)
        return

    json_content = generate_singbox_json(user_data["servers"])
    doc = BufferedInputFile(json_content.encode("utf-8"), filename="singbox_config.json")
    await callback.message.answer_document(
        document=doc,
        caption="🦊 <b>Полный профиль Sing-Box (JSON)</b>\nСодержит все ваши серверы.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    await callback.answer()

