import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, BufferedInputFile
import html

from .config import (
    DEFAULT_DEVICE_PROFILE,
    DEVICE_PRESETS,
    generate_random_hwid,
    build_headers_from_profile,
)
from .database import Database
from .parser import fetch_and_parse_subscription, clean_subscription_url
from .qr import generate_qr_code
from .keyboards import (
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_cancel_singbox_keyboard,
    get_single_link_keyboard,
    get_servers_inline_keyboard,
    get_server_detail_keyboard,
    get_qr_detail_keyboard,
    get_phone_setup_menu_keyboard,
    get_phone_os_keyboard,
    get_phone_app_back_keyboard,
    get_device_settings_keyboard,
    get_device_models_keyboard,
    get_device_action_success_keyboard,
    get_cancel_hwid_keyboard,
    get_device_info_back_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()


class SubscriptionState(StatesGroup):
    waiting_for_url = State()


class SingBoxState(StatesGroup):
    waiting_for_json = State()


class DeviceState(StatesGroup):
    waiting_for_hwid = State()


def get_db(message: Message) -> Database:
    return message.bot.db


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "👋 <b>Добро пожаловать в Happ Subscription Converter Bot!</b>\n\n"
        "Этот бот конвертирует подписки Happ Proxy в готовые ссылки <b>VLESS / Hysteria2</b> "
        "для приложений V2RayN, Streisand, v2rayNG, Hiddify, NekoBox и других.\n\n"
        "📌 <b>Главные функции:</b>\n"
        "• <b>📥 Вставить ссылку подписки</b> — спарсить защищённую подписку\n"
        "• <b>📋 Посмотреть ссылки</b> — список серверов и мгновенное копирование\n"
        "• <b>📷 QR-коды</b> — добавление серверов через камеру телефона\n"
        "• <b>📱 Настройки телефона и HWID</b> — управление эмуляцией смартфона, смена HWID и моделей устройств\n"
        "• <b>📖 Как подключить</b> — пошаговый мастер настройки клиентов на iOS и Android\n"
        "• <b>🔄 Обновить ссылки</b> — загрузить свежие ноды от провайдера\n\n"
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
        "2. Бот автоматически обратится к провайдеру с вашим HWID и профилем устройства, расшифрует подписку и выдаст список серверов.\n"
        "3. Нажмите на любой сервер, чтобы скопировать ссылку или получить <b>📷 QR-код</b> для телефона.\n"
        "4. В разделе <b>«📱 Настройки телефона и HWID»</b> вы можете сгенерировать новый HWID (для обхода лимита устройств) или выбрать модель смартфона.\n"
        "5. В разделе <b>«📖 Как подключить»</b> собраны пошаговые инструкции для iPhone и Android.\n\n"
        "Команды:\n"
        "/start — Главное меню\n"
        "/subscribe — Вставить ссылку\n"
        "/servers — Посмотреть серверы\n"
        "/device — Настройки телефона и HWID\n"
        "/connect — Инструкция по подключению\n"
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

    db: Database = message.bot.db
    profile = await db.get_user_device_profile(message.from_user.id)
    headers = build_headers_from_profile(profile)

    try:
        servers, raw_content = await fetch_and_parse_subscription(cleaned_url, headers=headers)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Ошибка при загрузке:</b>\n{html.escape(str(e))}", parse_mode="HTML")
        return

    # Сохраняем в базу данных
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
        f"📡 Найдено серверов: <b>{len(servers)}</b>\n"
        f"📱 Профиль устройства: <b>{html.escape(profile.get('model_name', 'Honor'))}</b> (HWID: <code>{html.escape(profile.get('hwid', '')[:8])}...</code>)\n\n"
        "👇 <b>Выберите сервер из списка, чтобы скопировать ссылку или получить QR-код:</b>"
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

    profile = await db.get_user_device_profile(message.from_user.id)
    headers = build_headers_from_profile(profile)

    try:
        servers, raw_content = await fetch_and_parse_subscription(sub_url, headers=headers)
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
        f"📡 Доступно серверов: <b>{len(servers)}</b>\n"
        f"📱 Использован HWID: <code>{html.escape(profile.get('hwid', ''))}</code>\n\n"
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


# Показ QR-кода выбранного сервера
@router.callback_query(F.data.startswith("qr:"))
async def callback_server_qr(callback: CallbackQuery):
    parts = callback.data.split(":")
    srv_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0

    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)
    if not user_data:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    target_srv = next((s for s in user_data["servers"] if s["id"] == srv_id), None)
    if not target_srv:
        await callback.answer("Сервер не найден.", show_alert=True)
        return

    try:
        qr_bytes = generate_qr_code(target_srv["link"])
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}")
        await callback.answer("Не удалось сгенерировать QR-код.", show_alert=True)
        return

    photo = BufferedInputFile(qr_bytes, filename=f"qr_server_{srv_id + 1}.png")
    title_safe = html.escape(target_srv["title"])
    proto_safe = html.escape(target_srv["proto"].upper())

    caption = (
        f"📷 <b>QR-код для подключения</b>\n"
        f"📡 <b>Сервер:</b> {title_safe}\n"
        f"⚙️ <b>Протокол:</b> <code>{proto_safe}</code>\n\n"
        f"📱 <i>Отсканируйте камерой приложения на телефоне:</i>\n"
        f"• <b>iOS:</b> Happ, Streisand, FoXray, V2Box\n"
        f"• <b>Android:</b> Happ, v2rayNG, Hiddify, NekoBox"
    )

    await callback.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=get_qr_detail_keyboard(target_srv["link"]),
        parse_mode="HTML",
    )
    await callback.answer()


# Удаление сервисного сообщения (например, скрытие QR-кода)
@router.callback_query(F.data == "delete_msg")
async def callback_delete_msg(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Не удалось удалить сообщение.")
        return
    await callback.answer()


# Переход в меню настройки телефона из выбранного сервера
@router.callback_query(F.data.startswith("phone_setup_from_srv:"))
async def callback_phone_setup_from_srv(callback: CallbackQuery):
    parts = callback.data.split(":")
    srv_id = parts[1]
    page = parts[2]
    back_srv = f"{srv_id}:{page}"

    text = (
        "📱 <b>Настройка подключения на телефоне</b>\n\n"
        "Подключить телефон можно двумя основными способами:\n\n"
        "1️⃣ <b>По QR-коду или ссылке на сервер</b> — нажмите «📷 QR-код» у сервера и отсканируйте его камерой приложения.\n"
        "2️⃣ <b>По ссылке на всю подписку</b> — добавьте ссылку подписки в приложение, чтобы все серверы обновлялись автоматически.\n\n"
        "👇 <b>Выберите вашу операционную систему:</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_phone_setup_menu_keyboard(back_srv=back_srv),
        parse_mode="HTML",
    )
    await callback.answer()


# ----------------------------------------------------
# Раздел: Настройки устройства и HWID эмуляции
# ----------------------------------------------------

async def render_device_settings_text(db: Database, user_id: int) -> tuple[str, bool]:
    profile = await db.get_user_device_profile(user_id)
    user_sub = await db.get_user_subscription(user_id)
    has_sub = bool(user_sub and user_sub.get("subscription_url"))

    hwid = html.escape(profile.get("hwid", "74jf74nf8f4jr5je"))
    model = html.escape(profile.get("model_name", profile.get("model", "Honor Magic 6 Pro")))
    os_info = html.escape(f"{profile.get('os', 'Android')} {profile.get('ver_os', '15')}")
    ua = html.escape(profile.get("user_agent", "Sing-box/1.8.29"))

    text = (
        "📱 <b>Настройки телефона и HWID (эмуляция устройства)</b>\n\n"
        "Провайдер подписки Happ требует, чтобы запрос к подписке выглядел как официальное мобильное приложение. "
        "Бот эмулирует смартфон и передаёт серверу провайдера следующие параметры:\n\n"
        f"🆔 <b>HWID устройства:</b> <code>{hwid}</code>\n"
        f"📱 <b>Модель смартфона:</b> <code>{model}</code>\n"
        f"⚙️ <b>Операционная система:</b> <code>{os_info}</code>\n"
        f"🌐 <b>Формат клиента:</b> <code>{ua}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Зачем нужны эти параметры?</b>\n"
        "• <b>Лимит устройств:</b> провайдер считает устройства по <b>HWID</b>. "
        "Если у вас закончились слоты (например, ошибка лимита) — нажмите <b>«🎲 Сгенерировать новый HWID»</b>, "
        "и сервер зарегистрирует абсолютно новый телефон.\n"
        "• <b>Свой настоящий телефон:</b> если хотите использовать те же параметры, "
        "что и ваш смартфон (не занимая лишний слот) — нажмите <b>«✏️ Ввести свой HWID»</b>.\n"
        "• <b>Модель телефона:</b> можно переключить на iPhone 15 Pro, Samsung S24 Ultra или Pixel в 1 клик."
    )
    return text, has_sub


# Главное меню настроек устройства из меню
@router.message(F.text == "📱 Настройки телефона и HWID")
@router.message(Command("device"))
@router.message(Command("hwid"))
async def show_device_settings(message: Message, state: FSMContext):
    await state.clear()
    db: Database = message.bot.db
    text, has_sub = await render_device_settings_text(db, message.from_user.id)
    await message.answer(
        text,
        reply_markup=get_device_settings_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )


# Возврат в настройки устройства
@router.callback_query(F.data == "dev_back")
async def callback_dev_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    db: Database = callback.bot.db
    text, has_sub = await render_device_settings_text(db, callback.from_user.id)
    await callback.message.edit_text(
        text,
        reply_markup=get_device_settings_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )
    await callback.answer()


# Генерация нового случайного HWID
@router.callback_query(F.data == "dev_gen_hwid")
async def callback_dev_gen_hwid(callback: CallbackQuery):
    db: Database = callback.bot.db
    new_hwid = generate_random_hwid(32)
    await db.update_user_device_profile(callback.from_user.id, hwid=new_hwid)

    user_sub = await db.get_user_subscription(callback.from_user.id)
    has_sub = bool(user_sub and user_sub.get("subscription_url"))

    text = (
        "🎲 <b>Сгенерирован новый уникальный HWID!</b>\n\n"
        f"🆔 <b>Новый HWID:</b> <code>{new_hwid}</code>\n\n"
        "✨ <b>Что это даёт:</b>\n"
        "Бот создал абсолютно новый идентификатор устройства. При следующем запросе сервер провайдера "
        "определит этот запрос как совершенно новое подключенное устройство (новый телефон).\n\n"
        "<i>Нажмите кнопку ниже, чтобы обновить подписку прямо сейчас с новым HWID:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_device_action_success_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )
    await callback.answer("Новый HWID успешно сгенерирован!")


# Меню выбора модели телефона
@router.callback_query(F.data == "dev_choose_model")
async def callback_dev_choose_model(callback: CallbackQuery):
    text = (
        "📱 <b>Выберите модель смартфона для эмуляции:</b>\n\n"
        "Бот будет передавать выбранную модель и версию операционной системы в заголовках к провайдеру.\n\n"
        "👇 <i>Выберите телефон из списка:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_device_models_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Сохранение выбранной модели
@router.callback_query(F.data.startswith("dev_set_model:"))
async def callback_dev_set_model(callback: CallbackQuery):
    preset_key = callback.data.split(":", 1)[1]
    preset = DEVICE_PRESETS.get(preset_key)

    if not preset:
        await callback.answer("Пресет не найден.", show_alert=True)
        return

    db: Database = callback.bot.db
    await db.update_user_device_profile(
        callback.from_user.id,
        model=preset["model"],
        model_name=preset["model_name"],
        os=preset["os"],
        ver_os=preset["ver_os"],
        user_agent=preset["user_agent"],
        locale=preset["locale"],
    )

    user_sub = await db.get_user_subscription(callback.from_user.id)
    has_sub = bool(user_sub and user_sub.get("subscription_url"))

    title = html.escape(preset["title"])
    text = (
        f"✅ <b>Модель устройства успешно изменена!</b>\n\n"
        f"📱 <b>Новый профиль:</b> {title}\n"
        f"⚙️ <b>Система:</b> <code>{preset['os']} {preset['ver_os']}</code>\n"
        f"🏷 <b>Код модели:</b> <code>{preset['model']}</code>\n\n"
        "Теперь бот отправляет серверу подписки эти параметры.\n\n"
        "<i>Нажмите кнопку ниже, чтобы применить настройки:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_device_action_success_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )
    await callback.answer("Модель смартфона сохранена!")


# Запрос ручного ввода HWID
@router.callback_query(F.data == "dev_input_hwid")
async def callback_dev_input_hwid(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeviceState.waiting_for_hwid)
    text = (
        "✏️ <b>Ручной ввод вашего HWID</b>\n\n"
        "Отправьте сообщением ваш уникальный HWID устройства.\n\n"
        "📌 <b>Требования:</b>\n"
        "• Строка из латинских букв и цифр\n"
        "• Длина от 8 до 64 символов (обычно 16 или 32 символа, например: <code>74jf74nf8f4jr5je</code> или <code>a1b2c3d4e5f6...</code>)\n\n"
        "<i>Отправьте HWID в чат или нажмите «Отмена»:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_hwid_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Отмена ввода HWID
@router.callback_query(F.data == "cancel_hwid_input")
async def callback_cancel_hwid_input(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    db: Database = callback.bot.db
    text, has_sub = await render_device_settings_text(db, callback.from_user.id)
    await callback.message.edit_text(
        text,
        reply_markup=get_device_settings_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )
    await callback.answer("Ввод отменён.")


# Обработка введённого HWID
@router.message(DeviceState.waiting_for_hwid)
async def process_user_hwid(message: Message, state: FSMContext):
    raw_hwid = message.text.strip()

    if len(raw_hwid) < 6 or len(raw_hwid) > 64 or " " in raw_hwid:
        await message.answer(
            "❌ <b>Некорректный формат HWID!</b>\n"
            "HWID должен быть строкой без пробелов длиной от 6 до 64 символов.\n"
            "Пожалуйста, отправьте корректный HWID или нажмите кнопку отмены:",
            reply_markup=get_cancel_hwid_keyboard(),
            parse_mode="HTML",
        )
        return

    db: Database = message.bot.db
    await db.update_user_device_profile(message.from_user.id, hwid=raw_hwid)
    await state.clear()

    user_sub = await db.get_user_subscription(message.from_user.id)
    has_sub = bool(user_sub and user_sub.get("subscription_url"))

    hwid_safe = html.escape(raw_hwid)
    text = (
        "✅ <b>Ваш HWID успешно сохранён!</b>\n\n"
        f"🆔 <b>Текущий HWID:</b> <code>{hwid_safe}</code>\n\n"
        "Теперь бот отправляет этот идентификатор серверу провайдера.\n\n"
        "<i>Нажмите кнопку ниже, чтобы обновить подписку с новым HWID:</i>"
    )
    await message.answer(
        text,
        reply_markup=get_device_action_success_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )


# Справка: как узнать HWID своего смартфона
@router.callback_query(F.data == "dev_hwid_info")
async def callback_dev_hwid_info(callback: CallbackQuery):
    text = (
        "📖 <b>Как узнать HWID своего смартфона?</b>\n\n"
        "<b>HWID (Hardware ID)</b> — это уникальный номер, который приложение <b>Happ Proxy</b> "
        "генерирует на вашем телефоне при первой установке.\n\n"
        "🔍 <b>Способ 1. В самом приложении Happ:</b>\n"
        "1. Откройте приложение <b>Happ</b> на смартфоне.\n"
        "2. Перейдите в <b>Настройки (Settings)</b> → <b>О приложении (About)</b> или проверьте раздел логов/диагностики.\n"
        "3. Найдите строку <b>Device ID</b> или <b>HWID</b>.\n\n"
        "🛠 <b>Способ 2. Через перехват запроса (Debug):</b>\n"
        "В документации проекта есть скрипт <code>debug_headers.php</code>. Если в приложении Happ вставить его адрес "
        "в поле подписки, приложение при обращении само пришлёт заголовок <code>X-Hwid</code>.\n\n"
        "💡 <b>Нужно ли обязательно узнавать свой настоящий HWID?</b>\n"
        "<b>Нет!</b> Самый простой способ — просто нажать кнопку <b>«🎲 Сгенерировать новый HWID»</b>. "
        "Бот сам создаст валидный случайный номер, и провайдер примет его как отдельный независимый телефон!"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_device_info_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Сброс на дефолтные настройки
@router.callback_query(F.data == "dev_reset_default")
async def callback_dev_reset_default(callback: CallbackQuery):
    db: Database = callback.bot.db
    await db.update_user_device_profile(
        callback.from_user.id,
        hwid=DEFAULT_DEVICE_PROFILE["hwid"],
        model=DEFAULT_DEVICE_PROFILE["model"],
        model_name=DEFAULT_DEVICE_PROFILE["model_name"],
        os=DEFAULT_DEVICE_PROFILE["os"],
        ver_os=DEFAULT_DEVICE_PROFILE["ver_os"],
        user_agent=DEFAULT_DEVICE_PROFILE["user_agent"],
        locale=DEFAULT_DEVICE_PROFILE["locale"],
    )

    user_sub = await db.get_user_subscription(callback.from_user.id)
    has_sub = bool(user_sub and user_sub.get("subscription_url"))

    text = (
        "🔄 <b>Настройки устройства сброшены на стандартные!</b>\n\n"
        f"📱 <b>Модель:</b> {DEFAULT_DEVICE_PROFILE['model_name']} ({DEFAULT_DEVICE_PROFILE['model']})\n"
        f"🆔 <b>HWID:</b> <code>{DEFAULT_DEVICE_PROFILE['hwid']}</code>\n"
        f"⚙️ <b>Система:</b> {DEFAULT_DEVICE_PROFILE['os']} {DEFAULT_DEVICE_PROFILE['ver_os']}\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_device_action_success_keyboard(has_sub=has_sub),
        parse_mode="HTML",
    )
    await callback.answer("Сброшено на стандартные настройки.")


# Обновление подписки прямо из настроек устройства
@router.callback_query(F.data == "dev_refresh_sub")
async def callback_dev_refresh_sub(callback: CallbackQuery):
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)

    if not user_data or not user_data.get("subscription_url"):
        await callback.answer("У вас ещё нет сохранённой подписки. Добавьте её в главном меню.", show_alert=True)
        return

    sub_url = user_data["subscription_url"]
    status_msg = await callback.message.answer("⏳ <i>Обновляю подписку от провайдера с вашим HWID...</i>", parse_mode="HTML")

    profile = await db.get_user_device_profile(callback.from_user.id)
    headers = build_headers_from_profile(profile)

    try:
        servers, raw_content = await fetch_and_parse_subscription(sub_url, headers=headers)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Ошибка при обновлении:</b>\n{html.escape(str(e))}", parse_mode="HTML")
        await callback.answer()
        return

    await db.save_user_subscription(
        user_id=callback.from_user.id,
        subscription_url=sub_url,
        servers=servers,
        raw_content=raw_content,
    )

    await status_msg.delete()
    text = (
        f"🔄 <b>Подписка успешно обновлена!</b>\n"
        f"🆔 Использован HWID: <code>{html.escape(profile.get('hwid', ''))}</code>\n"
        f"📡 Доступно серверов: <b>{len(servers)}</b>\n\n"
        "👇 Выберите сервер, чтобы скопировать ссылку или получить QR-код:"
    )
    await callback.message.answer(
        text,
        reply_markup=get_servers_inline_keyboard(servers, page=0),
        parse_mode="HTML",
    )
    await callback.answer("Подписка обновлена!")


# Инструкция по подключению клиентов
@router.message(F.text == "📖 Как подключить")
@router.message(F.text == "📱 Настройка телефона")
@router.message(Command("phone"))
@router.message(Command("setup"))
@router.message(Command("connect"))
async def show_phone_setup(message: Message):
    text = (
        "📖 <b>Инструкция по подключению на смартфоне</b>\n\n"
        "Подключить телефон можно двумя основными способами:\n\n"
        "1️⃣ <b>По QR-коду или ссылке на сервер</b> — выберите сервер в списке бота, нажмите «📷 QR-код» и отсканируйте камерой приложения.\n"
        "2️⃣ <b>По ссылке на всю подписку</b> — добавьте ссылку подписки в приложение, чтобы все серверы обновлялись автоматически.\n\n"
        "👇 <b>Выберите вашу операционную систему:</b>"
    )
    await message.answer(
        text,
        reply_markup=get_phone_setup_menu_keyboard(back_srv="none"),
        parse_mode="HTML",
    )


# Возврат в меню настройки телефона
@router.callback_query(F.data.startswith("phone_menu:"))
async def callback_phone_menu(callback: CallbackQuery):
    back_srv = callback.data.split(":", 1)[1]
    text = (
        "📱 <b>Настройка подключения на телефоне</b>\n\n"
        "👇 <b>Выберите вашу операционную систему:</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_phone_setup_menu_keyboard(back_srv=back_srv),
        parse_mode="HTML",
    )
    await callback.answer()


# Выбор ОС (iOS или Android)
@router.callback_query(F.data.startswith("phone_os:"))
async def callback_phone_os(callback: CallbackQuery):
    parts = callback.data.split(":")
    os_name = parts[1]
    back_srv = parts[2] if len(parts) > 2 else "none"

    if os_name == "ios":
        text = (
            "🍏 <b>Приложения для iPhone / iPad (iOS):</b>\n\n"
            "1️⃣ <b>Happ Proxy</b> — официальный клиент Happ. Нативная поддержка защищённых подписок.\n"
            "2️⃣ <b>Streisand</b> — один из лучших и удобных клиентов под iOS (VLESS, Hysteria, Reality, QR-код).\n"
            "3️⃣ <b>V2Box / FoXray</b> — альтернативные клиенты с мощной маршрутизацией.\n\n"
            "👇 <i>Нажмите на приложение, чтобы открыть пошаговую инструкцию:</i>"
        )
    else:
        text = (
            "🤖 <b>Приложения для Android:</b>\n\n"
            "1️⃣ <b>Happ Proxy</b> — официальный клиент с поддержкой подписок Happ.\n"
            "2️⃣ <b>v2rayNG</b> — стандарт индустрии на Android (быстрый, стабильный, импорт по QR и ссылкам).\n"
            "3️⃣ <b>Hiddify / NekoBox</b> — современные универсальные клиенты на ядре Sing-box.\n\n"
            "👇 <i>Нажмите на приложение, чтобы открыть пошаговую инструкцию:</i>"
        )

    await callback.message.edit_text(
        text,
        reply_markup=get_phone_os_keyboard(os_name=os_name, back_srv=back_srv),
        parse_mode="HTML",
    )
    await callback.answer()


# Подробная инструкция по конкретному приложению
@router.callback_query(F.data.startswith("phone_app:"))
async def callback_phone_app(callback: CallbackQuery):
    parts = callback.data.split(":")
    app_key = parts[1]
    back_srv = parts[2] if len(parts) > 2 else "none"

    os_name = "ios" if app_key.startswith("ios_") else "android"

    instructions = {
        "ios_happ": (
            "🍏 <b>Инструкция для Happ Proxy (iOS):</b>\n\n"
            "1. Установите <b>Happ Proxy Utility</b> из App Store.\n"
            "2. <b>Подключение по ссылке подписки:</b>\n"
            "   • Скопируйте ссылку вашей подписки (раздел «🔗 Подключение по ссылке»).\n"
            "   • Откройте Happ — приложение автоматически предложит импортировать ссылку из буфера.\n"
            "3. <b>Подключение через QR-код:</b>\n"
            "   • Выберите сервер в списке бота → нажмите <b>«📷 QR-код»</b>.\n"
            "   • В Happ нажмите <b>«+»</b> → <b>«Scan QR Code»</b>.\n"
            "4. Выберите нужную локацию и нажмите кнопку включения."
        ),
        "ios_streisand": (
            "🍏 <b>Инструкция для Streisand (iOS):</b>\n\n"
            "1. Установите <b>Streisand</b> из App Store.\n"
            "2. <b>Способ 1 — QR-код (самый быстрый):</b>\n"
            "   • В боте выберите сервер → нажмите <b>«📷 QR-код»</b>.\n"
            "   • В Streisand нажмите <b>«+»</b> в правом верхнем углу → <b>«Scan QR Code»</b>.\n"
            "   • Конфигурация моментально добавится.\n"
            "3. <b>Способ 2 — Через буфер обмена:</b>\n"
            "   • Нажмите <b>«📋 Скопировать»</b> у сервера в боте.\n"
            "   • В Streisand нажмите <b>«+»</b> → <b>«Import from Clipboard»</b>.\n"
            "4. <b>Способ 3 — Все серверы разом:</b>\n"
            "   • Скачайте файл <b>«📁 Все ссылки (.txt)»</b> из бота и откройте через «Поделиться» → Streisand."
        ),
        "ios_v2box": (
            "🍏 <b>Инструкция для V2Box / FoXray (iOS):</b>\n\n"
            "1. Установите <b>V2Box</b> или <b>FoXray</b> из App Store.\n"
            "2. <b>Подключение сервера:</b>\n"
            "   • Нажмите <b>«📷 QR-код»</b> у сервера в боте и отсканируйте через значок камеры в V2Box.\n"
            "   • Либо скопируйте VLESS-ссылку и нажмите <b>«+» → «Import V2ray from Clipboard»</b>.\n"
            "3. Нажмите кнопку <b>«Slide to connect»</b>."
        ),
        "and_happ": (
            "🤖 <b>Инструкция для Happ Proxy (Android):</b>\n\n"
            "1. Установите клиент <b>Happ</b> на ваш Android-смартфон.\n"
            "2. <b>Подключение по ссылке:</b>\n"
            "   • Скопируйте ссылку подписки в боте.\n"
            "   • В приложении Happ нажмите <b>«+»</b> → <b>«Add subscription»</b> и вставьте ссылку.\n"
            "3. <b>Подключение через QR:</b>\n"
            "   • В боте выберите сервер → <b>«📷 QR-код»</b>.\n"
            "   • В Happ нажмите <b>«+» → «Scan QR»</b>.\n"
            "4. Нажмите круглую кнопку подключения."
        ),
        "and_v2rayng": (
            "🤖 <b>Инструкция для v2rayNG (Android):</b>\n\n"
            "1. Установите <b>v2rayNG</b> из Google Play или с GitHub.\n"
            "2. <b>Способ через QR-код:</b>\n"
            "   • В боте выберите сервер → <b>«📷 QR-код»</b>.\n"
            "   • В v2rayNG нажмите <b>«+»</b> вверху экрана → <b>«Сканировать QR-код»</b>.\n"
            "3. <b>Способ через буфер:</b>\n"
            "   • В боте нажмите <b>«📋 Скопировать»</b> у сервера.\n"
            "   • В v2rayNG нажмите <b>«+» → «Импортировать профиль из буфера обмена»</b>.\n"
            "4. Нажмите значок <b>V</b> в правом нижнем углу для включения."
        ),
        "and_hiddify": (
            "🤖 <b>Инструкция для Hiddify / NekoBox (Android):</b>\n\n"
            "1. Установите <b>Hiddify</b> из Google Play или GitHub.\n"
            "2. <b>Быстрое добавление:</b>\n"
            "   • Скопируйте ссылку сервера или отсканируйте QR-код через значок сканера на главном экране.\n"
            "3. Нажмите большую круглую кнопку подключения по центру."
        ),
    }

    text = instructions.get(app_key, "Инструкция временно недоступна.")
    await callback.message.edit_text(
        text,
        reply_markup=get_phone_app_back_keyboard(os_name=os_name, back_srv=back_srv),
        parse_mode="HTML",
    )
    await callback.answer()


# Информация о подключении всей подписки по ссылке
@router.callback_query(F.data.startswith("phone_sub_info:"))
async def callback_phone_sub_info(callback: CallbackQuery):
    back_srv = callback.data.split(":", 1)[1]
    db: Database = callback.bot.db
    user_data = await db.get_user_subscription(callback.from_user.id)

    sub_url = user_data.get("subscription_url") if user_data else None

    if sub_url:
        sub_safe = html.escape(sub_url)
        text = (
            "🔗 <b>Подключение всей подписки по ссылке</b>\n\n"
            "Ваша сохранённая ссылка подписки:\n"
            f"<code>{sub_safe}</code>\n\n"
            "💡 <b>Как это работает на телефоне:</b>\n"
            "• В приложении (<b>Happ</b>, <b>v2rayNG</b> и др.) откройте раздел <i>«Подписки» (Subscription Groups)</i>.\n"
            "• Добавьте эту ссылку и нажмите <i>«Обновить подписки»</i>.\n"
            "• Все серверы скачаются автоматически и будут сами обновляться по расписанию!\n\n"
            "⚠️ <i>Примечание: если провайдер Happ блокирует прямые запросы от сторонних клиентов (ошибка 403), используйте приложение Happ, либо импортируйте конкретные серверы через QR-код / TXT файл из бота.</i>"
        )
    else:
        text = (
            "🔗 <b>Подключение всей подписки по ссылке</b>\n\n"
            "У вас ещё не сохранена ссылка на подписку.\n\n"
            "Нажмите <b>«📥 Вставить ссылку подписки»</b> в главном меню, чтобы добавить её.\n"
            "После добавления бот расшифрует серверы и выдаст готовые конфигурации для любых приложений."
        )

    await callback.message.edit_text(
        text,
        reply_markup=get_phone_setup_menu_keyboard(back_srv=back_srv),
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


from .converters import (
    generate_clash_yaml,
    generate_singbox_json,
    convert_singbox_json_to_links,
)


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


# ========================================================
# Конвертер Sing-Box -> VLESS (из файла или текста)
# ========================================================

@router.message(F.text == "🦊 Конвертер Sing-Box → VLESS")
@router.message(Command("singbox2vless"))
async def prompt_singbox_convert(message: Message, state: FSMContext):
    await state.set_state(SingBoxState.waiting_for_json)
    text = (
        "🦊 <b>Конвертер Sing-Box в VLESS / Hysteria2</b>\n\n"
        "Отправьте мне конфигурацию Sing-Box:\n"
        "• 📎 <b>Файлом</b> (с расширением <code>.json</code> или <code>.txt</code>)\n"
        "• 💬 <b>Или текстом</b> (вставьте JSON-код прямо в чат)\n\n"
        "<i>Бот извлечет все outbound-серверы и выдаст готовые ссылки.</i>"
    )
    await message.answer(text, reply_markup=get_cancel_singbox_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "cancel_singbox")
async def callback_cancel_singbox(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Конвертация Sing-Box отменена.")
    await callback.answer()


@router.message(SingBoxState.waiting_for_json)
async def process_singbox_content(message: Message, state: FSMContext):
    # Обработка текстовой отмены
    if message.text and message.text.strip().lower() in ("отмена", "❌ отмена", "/cancel"):
        await state.clear()
        await message.answer("❌ Конвертация Sing-Box отменена.", reply_markup=get_main_menu_keyboard())
        return

    raw_text = ""
    if message.document:
        if message.document.file_size and message.document.file_size > 15 * 1024 * 1024:
            await message.answer("❌ Файл слишком большой (максимум 15 МБ).")
            return

        status_msg = await message.answer("⏳ <i>Скачиваю и обрабатываю файл...</i>", parse_mode="HTML")
        try:
            file_io = await message.bot.download(message.document)
            raw_text = file_io.read().decode("utf-8", errors="replace")
        except Exception as e:
            await status_msg.edit_text(f"❌ Ошибка при чтении файла: {e}")
            return
        await status_msg.delete()
    elif message.text:
        raw_text = message.text.strip()
    else:
        await message.answer(
            "⚠️ Пожалуйста, отправьте текстовый JSON-файл или текстовое сообщение с кодом.",
            reply_markup=get_cancel_singbox_keyboard(),
        )
        return

    import json
    try:
        data = json.loads(raw_text)
    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка JSON:</b> Не удалось распознать JSON-формат:\n<code>{html.escape(str(e))}</code>\n\n"
            "Пожалуйста, отправьте корректный JSON-файл или сообщение.",
            reply_markup=get_cancel_singbox_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        results = convert_singbox_json_to_links(data)
    except Exception as e:
        await message.answer(
            f"❌ Ошибка конвертации: {html.escape(str(e))}",
            reply_markup=get_cancel_singbox_keyboard(),
            parse_mode="HTML",
        )
        return

    if not results:
        await message.answer(
            "⚠️ <b>В присланном конфиге не найдено поддерживаемых прокси-серверов.</b>\n\n"
            "Убедитесь, что в конфиге есть секция <code>outbounds</code> с серверами типа <code>vless</code>, <code>hysteria2</code> или <code>trojan</code>.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.clear()

    if len(results) == 1:
        item = results[0]
        text = (
            "✅ <b>Сервер успешно сконвертирован в VLESS!</b>\n\n"
            f"📡 <b>Название:</b> <code>{html.escape(item['tag'])}</code>\n"
            f"⚙️ <b>Протокол:</b> <code>{html.escape(item['proto'].upper())}</code>\n\n"
            "👇 <b>Нажмите на блок ниже, чтобы скопировать ссылку:</b>\n"
            f"<code>{html.escape(item['link'])}</code>"
        )
        await message.answer(
            text,
            reply_markup=get_single_link_keyboard(item["link"]),
            parse_mode="HTML",
        )
    else:
        lines_text = []
        for i, item in enumerate(results[:5], 1):
            lines_text.append(f"{i}. <b>{html.escape(item['tag'])}</b> (<code>{item['proto'].upper()}</code>)")

        preview = "\n".join(lines_text)
        if len(results) > 5:
            preview += f"\n<i>... и ещё {len(results) - 5} серверов</i>"

        text = (
            f"✅ <b>Успешно сконвертировано серверов: {len(results)}</b>\n\n"
            f"{preview}\n\n"
            "📁 <i>Все ссылки сформированы в прикреплённый файл ниже:</i>"
        )
        await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

        all_links_content = "\n".join(r["link"] for r in results).encode("utf-8")
        doc = BufferedInputFile(all_links_content, filename="vless_from_singbox.txt")
        await message.answer_document(
            document=doc,
            caption=f"📁 Ссылки VLESS / Hysteria2 ({len(results)} шт.) для импорта в V2RayN, v2rayNG, Streisand",
        )


