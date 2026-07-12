"""
Telegram-бот каталог товаров с корзиной.
Демо-проект для портфолио Kwork.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Укажи BOT_TOKEN в файле .env")

ORDERS_FILE = Path(__file__).parent / "orders.json"

PRODUCTS = {
    "tshirt": {"name": "Футболка оверсайз", "price": 1890, "emoji": "👕"},
    "hoodie": {"name": "Худи с принтом", "price": 3490, "emoji": "🧥"},
    "cap": {"name": "Кепка", "price": 990, "emoji": "🧢"},
    "bag": {"name": "Шоппер", "price": 790, "emoji": "👜"},
    "socks": {"name": "Носки (3 пары)", "price": 590, "emoji": "🧦"},
    "mug": {"name": "Кружка", "price": 690, "emoji": "☕"},
}


class OrderStates(StatesGroup):
    entering_name = State()
    entering_phone = State()
    entering_address = State()


def load_orders() -> list:
    if ORDERS_FILE.exists():
        with open(ORDERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_order(order: dict) -> None:
    orders = load_orders()
    orders.append(order)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def format_cart(cart: dict) -> str:
    if not cart:
        return "Корзина пуста"
    lines = []
    total = 0
    for key, qty in cart.items():
        p = PRODUCTS[key]
        subtotal = p["price"] * qty
        total += subtotal
        lines.append(f"{p['emoji']} {p['name']} × {qty} = {subtotal} ₽")
    lines.append(f"\n<b>Итого: {total} ₽</b>")
    return "\n".join(lines)


def catalog_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{p['emoji']} {p['name']} — {p['price']} ₽",
            callback_data=f"add:{key}",
        )]
        for key, p in PRODUCTS.items()
    ]
    rows.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")])
    rows.append([InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart_kb(cart: dict) -> InlineKeyboardMarkup:
    rows = []
    if cart:
        rows.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
        rows.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear")])
    rows.append([InlineKeyboardButton(text="◀️ В каталог", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(cart={})
    await message.answer(
        "🛍 Добро пожаловать в <b>Shop Demo</b>!\n\n"
        "Интернет-магазин прямо в Telegram — "
        "выбирайте товары, добавляйте в корзину и оформляйте заказ.\n\n"
        "Выберите товар:",
        reply_markup=catalog_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍 <b>Каталог товаров:</b>\n\nВыберите товар:",
        reply_markup=catalog_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("add:"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[1]
    data = await state.get_data()
    cart = data.get("cart", {})
    cart[key] = cart.get(key, 0) + 1
    await state.update_data(cart=cart)
    p = PRODUCTS[key]
    await callback.answer(f"✅ {p['name']} добавлен в корзину!", show_alert=False)


@dp.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    await callback.message.edit_text(
        f"🛒 <b>Ваша корзина:</b>\n\n{format_cart(cart)}",
        reply_markup=cart_kb(cart),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "clear")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await callback.message.edit_text(
        "🛒 Корзина очищена.\n\nВыберите товар:",
        reply_markup=catalog_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 <b>Shop Demo</b>\n\n"
        "📍 Доставка по всей России\n"
        "📞 +7 (999) 123-45-67\n"
        "📸 @shop_demo\n"
        "🕐 Пн–Пт 10:00–19:00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В каталог", callback_data="catalog")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    await state.set_state(OrderStates.entering_name)
    await callback.message.edit_text(
        f"📦 <b>Оформление заказа</b>\n\n{format_cart(cart)}\n\n"
        f"Введите ваше <b>имя</b>:",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(OrderStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text.strip())
    await state.set_state(OrderStates.entering_phone)
    await message.answer("📞 Введите <b>номер телефона</b>:", parse_mode="HTML")


@dp.message(OrderStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    await state.update_data(client_phone=message.text.strip())
    await state.set_state(OrderStates.entering_address)
    await message.answer("📍 Введите <b>адрес доставки</b>:", parse_mode="HTML")


@dp.message(OrderStates.entering_address)
async def enter_address(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    total = sum(PRODUCTS[k]["price"] * q for k, q in cart.items())

    order = {
        "id": len(load_orders()) + 1,
        "user_id": message.from_user.id,
        "cart": {PRODUCTS[k]["name"]: q for k, q in cart.items()},
        "total": total,
        "name": data["client_name"],
        "phone": data["client_phone"],
        "address": message.text.strip(),
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    save_order(order)
    await state.clear()
    await state.update_data(cart={})

    await message.answer(
        "✅ <b>Заказ оформлен!</b>\n\n"
        f"📦 {format_cart(cart)}\n"
        f"👤 {data['client_name']}\n"
        f"📞 {data['client_phone']}\n"
        f"📍 {message.text.strip()}\n\n"
        "Менеджер свяжется с вами для подтверждения. Спасибо!",
        reply_markup=catalog_kb(),
        parse_mode="HTML",
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
