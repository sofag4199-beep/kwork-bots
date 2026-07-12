"""
Telegram-бот для записи в салон красоты.
Демо-проект для портфолио Kwork.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Укажи BOT_TOKEN в файле .env")

OWNER_ID = os.getenv("OWNER_ID")
if OWNER_ID:
    OWNER_ID = int(OWNER_ID)

BOOKINGS_FILE = Path(__file__).parent / "bookings.json"

SERVICES = {
    "manicure": {"name": "Маникюр", "price": "от 1200 ₽", "time": "60 мин"},
    "pedicure": {"name": "Педикюр", "price": "от 1500 ₽", "time": "75 мин"},
    "haircut": {"name": "Стрижка", "price": "от 1800 ₽", "time": "45 мин"},
    "coloring": {"name": "Окрашивание", "price": "от 3500 ₽", "time": "120 мин"},
    "brows": {"name": "Брови", "price": "от 800 ₽", "time": "30 мин"},
}

TIME_SLOTS = [
    "10:00", "11:00", "12:00", "13:00", "14:00",
    "15:00", "16:00", "17:00", "18:00", "19:00",
]


class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()


def load_bookings() -> list:
    if BOOKINGS_FILE.exists():
        with open(BOOKINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_booking(booking: dict) -> None:
    bookings = load_bookings()
    bookings.append(booking)
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
        [InlineKeyboardButton(text="💅 Наши услуги", callback_data="services")],
        [InlineKeyboardButton(text="📍 Адрес и контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="❓ Как это работает", callback_data="howto")],
    ])


def services_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{s['name']} — {s['price']}",
            callback_data=f"service:{key}",
        )]
        for key, s in SERVICES.items()
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(TIME_SLOTS), 2):
        row = [
            InlineKeyboardButton(text=TIME_SLOTS[i], callback_data=f"time:{TIME_SLOTS[i]}")
        ]
        if i + 1 < len(TIME_SLOTS):
            row.append(
                InlineKeyboardButton(text=TIME_SLOTS[i + 1], callback_data=f"time:{TIME_SLOTS[i + 1]}")
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="book")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в <b>Beauty Studio</b>!\n\n"
        "Здесь вы можете записаться на услугу онлайн — "
        "быстро, без звонков и ожидания на линии.\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Добро пожаловать в <b>Beauty Studio</b>!\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "services")
async def show_services(callback: CallbackQuery):
    text = "💅 <b>Наши услуги:</b>\n\n"
    for s in SERVICES.values():
        text += f"• <b>{s['name']}</b> — {s['price']} ({s['time']})\n"
    text += "\nНажмите «Записаться», чтобы выбрать услугу."
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    await callback.message.edit_text(
        "📍 <b>Beauty Studio</b>\n\n"
        "🏠 Адрес: ул. Примерная, 15, ТЦ «Галерея», 2 этаж\n"
        "📞 Телефон: +7 (999) 123-45-67\n"
        "🕐 Работаем: Пн–Сб 10:00–20:00\n"
        "📸 Instagram: @beauty_studio_demo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "howto")
async def show_howto(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Как записаться:</b>\n\n"
        "1️⃣ Нажмите «Записаться»\n"
        "2️⃣ Выберите услугу\n"
        "3️⃣ Выберите удобное время\n"
        "4️⃣ Укажите имя и телефон\n"
        "5️⃣ Готово! Мы подтвердим запись в течение 15 минут\n\n"
        "Отмена записи — просто напишите нам в чат.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text(
        "💅 Выберите услугу:",
        reply_markup=services_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("service:"), BookingStates.choosing_service)
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_key = callback.data.split(":")[1]
    service = SERVICES[service_key]
    await state.update_data(service_key=service_key, service_name=service["name"])
    await state.set_state(BookingStates.choosing_time)
    await callback.message.edit_text(
        f"✅ Услуга: <b>{service['name']}</b> ({service['price']})\n\n"
        f"🕐 Выберите удобное время:",
        reply_markup=time_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("time:"), BookingStates.choosing_time)
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time_slot = callback.data.split(":")[1]
    await state.update_data(time_slot=time_slot)
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        f"🕐 Время: <b>{time_slot}</b>\n\n"
        f"Введите ваше <b>имя</b>:",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя:")
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer(
        f"👤 Имя: <b>{name}</b>\n\n"
        f"Теперь введите ваш <b>номер телефона</b>:",
        parse_mode="HTML",
    )


@dp.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 7:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return

    data = await state.get_data()
    booking = {
        "id": len(load_bookings()) + 1,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "—",
        "service": data["service_name"],
        "time": data["time_slot"],
        "name": data["client_name"],
        "phone": phone,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    save_booking(booking)
    await state.clear()

    if OWNER_ID:
        try:
            await bot.send_message(
                OWNER_ID,
                "🔔 <b>Новая запись!</b>\n\n"
                f"💅 {data['service_name']}\n"
                f"🕐 {data['time_slot']}\n"
                f"👤 {data['client_name']}\n"
                f"📞 {phone}\n"
                f"📅 {booking['created_at']}\n\n"
                f"Telegram: @{message.from_user.username or '—'}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Не удалось отправить уведомление владельцу: %s", e)

    await message.answer(
        "✅ <b>Запись оформлена!</b>\n\n"
        f"💅 Услуга: {data['service_name']}\n"
        f"🕐 Время: {data['time_slot']}\n"
        f"👤 Имя: {data['client_name']}\n"
        f"📞 Телефон: {phone}\n\n"
        "Мы свяжемся с вами для подтверждения в течение 15 минут.\n"
        "Спасибо, что выбрали Beauty Studio! 💖",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@dp.message(Command("bookings"))
async def cmd_bookings(message: Message):
    """Команда для владельца — посмотреть все записи."""
    if OWNER_ID and message.from_user.id != OWNER_ID:
        await message.answer("Эта команда только для владельца салона.")
        return
    bookings = load_bookings()
    if not bookings:
        await message.answer("Записей пока нет.")
        return
    text = "📋 <b>Все записи:</b>\n\n"
    for b in bookings[-10:]:
        text += (
            f"#{b['id']} | {b['created_at']}\n"
            f"  {b['service']} в {b['time']}\n"
            f"  {b['name']}, {b['phone']}\n\n"
        )
    await message.answer(text, parse_mode="HTML")


async def start_health_server() -> None:
    """Render требует открытый HTTP-порт, иначе сервис остановят."""
    from aiohttp import web

    async def health(_request):
        return web.Response(text="Bot is running")

    app = web.Application()
    app.router.add_get("/", health)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info("Health server on port %s", port)


async def main():
    logger.info("Бот запущен")
    await start_health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
