"""
Telegram FAQ-бот для бизнеса (кафе/магазин/услуги).
Демо-проект для портфолио Kwork.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Укажи BOT_TOKEN в файле .env")

FAQ = {
    "hours": {
        "q": "🕐 Режим работы",
        "a": "Мы работаем ежедневно с 9:00 до 22:00.\n"
             "В праздничные дни — с 10:00 до 21:00.",
    },
    "menu": {
        "q": "🍽 Меню и цены",
        "a": "Актуальное меню и цены — на нашем сайте или в разделе «Меню».\n"
             "Средний чек: 500–800 ₽.\n"
             "Есть бизнес-ланчи с 12:00 до 15:00 — от 350 ₽.",
    },
    "delivery": {
        "q": "🚗 Доставка",
        "a": "Доставляем по городу за 40–60 минут.\n"
             "Минимальный заказ: 800 ₽.\n"
             "Доставка бесплатная при заказе от 1500 ₽.\n"
             "Заказать: через бота или по телефону +7 (999) 123-45-67.",
    },
    "booking": {
        "q": "📅 Бронь столика",
        "a": "Забронировать столик можно:\n"
             "• Через этого бота (кнопка «Забронировать»)\n"
             "• По телефону: +7 (999) 123-45-67\n"
             "• В Instagram: @cafe_demo\n\n"
             "Бронь держим 15 минут.",
    },
    "payment": {
        "q": "💳 Оплата",
        "a": "Принимаем:\n"
             "• Наличные\n"
             "• Банковские карты\n"
             "• СБП\n"
             "• Оплата при доставке или онлайн",
    },
    "parking": {
        "q": "🅿️ Парковка",
        "a": "Бесплатная парковка для гостей — 20 мест во дворе.\n"
             "Въезд с ул. Примерная, 10.",
    },
}


def main_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=v["q"], callback_data=f"faq:{k}")]
        for k, v in FAQ.items()
    ]
    rows.append([InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact")])
    rows.append([InlineKeyboardButton(text="📅 Забронировать столик", callback_data="reserve")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ К списку вопросов", callback_data="back")],
        [InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact")],
    ])


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "☕ Добро пожаловать в <b>Café Demo</b>!\n\n"
        "Я помогу ответить на частые вопросы — "
        "режим работы, меню, доставка, бронь и другое.\n\n"
        "Выберите интересующий вопрос:",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "back")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "☕ <b>Café Demo</b> — выберите вопрос:",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("faq:"))
async def show_faq(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    item = FAQ[key]
    await callback.message.edit_text(
        f"<b>{item['q']}</b>\n\n{item['a']}",
        reply_markup=back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "contact")
async def show_contact(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 <b>Связаться с нами:</b>\n\n"
        "📍 Адрес: ул. Примерная, 10\n"
        "📞 Телефон: +7 (999) 123-45-67\n"
        "📸 Instagram: @cafe_demo\n"
        "✉️ Email: hello@cafe-demo.ru\n\n"
        "Отвечаем в рабочее время в течение 30 минут.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К списку вопросов", callback_data="back")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "reserve")
async def show_reserve(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 <b>Бронь столика</b>\n\n"
        "Чтобы забронировать, напишите нам:\n"
        "• Дату и время\n"
        "• Количество гостей\n"
        "• Ваше имя и телефон\n\n"
        "Или позвоните: +7 (999) 123-45-67\n\n"
        "Мы подтвердим бронь в течение 15 минут.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К списку вопросов", callback_data="back")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
