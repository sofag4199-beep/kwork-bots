"""
VK-бот для записи в салон красоты.
Демо-проект для портфолио Kwork.
"""

import json
import logging
import os
import random
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VK_TOKEN = (os.getenv("VK_TOKEN") or "").strip()
VK_GROUP_ID = (os.getenv("VK_GROUP_ID") or "").strip()
OWNER_ID = (os.getenv("OWNER_ID") or "").strip()

if not VK_TOKEN:
    raise ValueError("Укажи VK_TOKEN (Render → Environment или .env)")
if not VK_GROUP_ID:
    raise ValueError("Укажи VK_GROUP_ID (должно быть 240240392)")

try:
    VK_GROUP_ID = int(VK_GROUP_ID)
except ValueError as exc:
    raise ValueError(f"VK_GROUP_ID должен быть числом, сейчас: {VK_GROUP_ID!r}") from exc

OWNER_ID = int(OWNER_ID) if OWNER_ID else None

logger.info("Старт: group_id=%s, token=%s...", VK_GROUP_ID, VK_TOKEN[:12])

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

user_states: dict[int, dict] = {}


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


def get_state(user_id: int) -> dict:
    if user_id not in user_states:
        user_states[user_id] = {"step": None, "data": {}}
    return user_states[user_id]


def clear_state(user_id: int) -> None:
    user_states[user_id] = {"step": None, "data": {}}


def send(vk, peer_id: int, text: str, keyboard: VkKeyboard | None = None) -> None:
    params = {
        "peer_id": peer_id,
        "message": text,
        "random_id": random.randint(1, 2**31),
    }
    if keyboard:
        params["keyboard"] = keyboard.get_keyboard()
    try:
        vk.messages.send(**params)
    except vk_api.exceptions.ApiError as exc:
        # 912 = в группе не включены «Возможности ботов» (клавиатуры)
        if exc.code == 912 and keyboard:
            logger.warning("Клавиатура недоступна (ошибка 912) — отправляю текстом")
            params.pop("keyboard", None)
            vk.messages.send(**params)
        else:
            raise


def main_menu_kb() -> VkKeyboard:
    kb = VkKeyboard(one_time=False)
    kb.add_button("Записаться", color=VkKeyboardColor.POSITIVE)
    kb.add_button("Услуги", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("Контакты", color=VkKeyboardColor.PRIMARY)
    kb.add_button("Как записаться", color=VkKeyboardColor.SECONDARY)
    return kb


def services_kb() -> VkKeyboard:
    kb = VkKeyboard(one_time=False)
    for key, service in SERVICES.items():
        kb.add_button(service["name"], color=VkKeyboardColor.PRIMARY)
        kb.add_line()
    kb.add_button("В меню", color=VkKeyboardColor.SECONDARY)
    return kb


def time_kb() -> VkKeyboard:
    kb = VkKeyboard(one_time=False)
    for i, slot in enumerate(TIME_SLOTS):
        if i and i % 2 == 0:
            kb.add_line()
        kb.add_button(slot, color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("Назад", color=VkKeyboardColor.SECONDARY)
    return kb


def back_main_kb() -> VkKeyboard:
    kb = VkKeyboard(one_time=False)
    kb.add_button("Записаться", color=VkKeyboardColor.POSITIVE)
    kb.add_button("В меню", color=VkKeyboardColor.SECONDARY)
    return kb


def welcome_text() -> str:
    return (
        "👋 Добро пожаловать в Beauty Studio!\n\n"
        "Запишитесь на услугу онлайн — быстро и без звонков.\n\n"
        "Выберите действие:"
    )


def show_main(vk, peer_id: int) -> None:
    send(vk, peer_id, welcome_text(), main_menu_kb())


def show_services(vk, peer_id: int) -> None:
    text = "💅 Наши услуги:\n\n"
    for service in SERVICES.values():
        text += f"• {service['name']} — {service['price']} ({service['time']})\n"
    text += "\nНажмите «Записаться», чтобы выбрать услугу."
    send(vk, peer_id, text, back_main_kb())


def show_contacts(vk, peer_id: int) -> None:
    send(
        vk,
        peer_id,
        "📍 Beauty Studio\n\n"
        "🏠 Адрес: ул. Примерная, 15, ТЦ «Галерея», 2 этаж\n"
        "📞 Телефон: +7 (999) 123-45-67\n"
        "🕐 Работаем: Пн–Сб 10:00–20:00\n"
        "📸 VK: Beauty Studio",
        back_main_kb(),
    )


def show_howto(vk, peer_id: int) -> None:
    send(
        vk,
        peer_id,
        "❓ Как записаться:\n\n"
        "1️⃣ Нажмите «Записаться»\n"
        "2️⃣ Выберите услугу\n"
        "3️⃣ Выберите удобное время\n"
        "4️⃣ Укажите имя и телефон\n"
        "5️⃣ Готово! Мы подтвердим запись в течение 15 минут",
        back_main_kb(),
    )


def notify_owner(vk, booking: dict, user_id: int) -> None:
    if not OWNER_ID:
        return
    try:
        send(
            vk,
            OWNER_ID,
            "🔔 Новая запись (VK)!\n\n"
            f"💅 {booking['service']}\n"
            f"🕐 {booking['time']}\n"
            f"👤 {booking['name']}\n"
            f"📞 {booking['phone']}\n"
            f"📅 {booking['created_at']}\n\n"
            f"VK ID: {user_id}",
        )
    except Exception as exc:
        logger.warning("Не удалось уведомить владельца: %s", exc)


def finish_booking(vk, peer_id: int, user_id: int, phone: str) -> None:
    state = get_state(user_id)
    data = state["data"]
    booking = {
        "id": len(load_bookings()) + 1,
        "user_id": user_id,
        "service": data["service_name"],
        "time": data["time_slot"],
        "name": data["client_name"],
        "phone": phone,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    save_booking(booking)
    notify_owner(vk, booking, user_id)
    clear_state(user_id)

    send(
        vk,
        peer_id,
        "✅ Запись оформлена!\n\n"
        f"💅 Услуга: {data['service_name']}\n"
        f"🕐 Время: {data['time_slot']}\n"
        f"👤 Имя: {data['client_name']}\n"
        f"📞 Телефон: {phone}\n\n"
        "Мы свяжемся с вами для подтверждения в течение 15 минут.\n"
        "Спасибо, что выбрали Beauty Studio! 💖",
        main_menu_kb(),
    )


def handle_payload(vk, user_id: int, peer_id: int, payload: dict) -> None:
    cmd = payload.get("cmd")

    if cmd == "main":
        clear_state(user_id)
        show_main(vk, peer_id)
        return

    if cmd == "services":
        show_services(vk, peer_id)
        return

    if cmd == "contacts":
        show_contacts(vk, peer_id)
        return

    if cmd == "howto":
        show_howto(vk, peer_id)
        return

    if cmd == "book":
        state = get_state(user_id)
        state["step"] = "choosing_service"
        state["data"] = {}
        send(vk, peer_id, "💅 Выберите услугу:", services_kb())
        return

    if cmd == "service":
        key = payload.get("key")
        if key not in SERVICES:
            send(vk, peer_id, "Услуга не найдена. Выберите из списка:", services_kb())
            return
        service = SERVICES[key]
        state = get_state(user_id)
        state["step"] = "choosing_time"
        state["data"] = {
            "service_key": key,
            "service_name": service["name"],
        }
        send(
            vk,
            peer_id,
            f"✅ Услуга: {service['name']} ({service['price']})\n\n🕐 Выберите удобное время:",
            time_kb(),
        )
        return

    if cmd == "time":
        slot = payload.get("slot")
        if slot not in TIME_SLOTS:
            send(vk, peer_id, "Выберите время из списка:", time_kb())
            return
        state = get_state(user_id)
        state["step"] = "entering_name"
        state["data"]["time_slot"] = slot
        send(vk, peer_id, f"🕐 Время: {slot}\n\nВведите ваше имя:")


def handle_text(vk, user_id: int, peer_id: int, text: str) -> None:
    lowered = text.lower().strip()
    logger.info("Сообщение от %s: %s", user_id, text)

    if OWNER_ID and user_id == OWNER_ID and lowered in ("записи", "/записи", "bookings"):
        bookings = load_bookings()
        if not bookings:
            send(vk, peer_id, "Записей пока нет.")
            return
        msg = "📋 Все записи:\n\n"
        for booking in bookings[-10:]:
            msg += (
                f"#{booking['id']} | {booking['created_at']}\n"
                f"  {booking['service']} в {booking['time']}\n"
                f"  {booking['name']}, {booking['phone']}\n\n"
            )
        send(vk, peer_id, msg)
        return

    state = get_state(user_id)
    step = state["step"]

    if step == "entering_name":
        name = text.strip()
        if len(name) < 2:
            send(vk, peer_id, "Пожалуйста, введите корректное имя:")
            return
        state["data"]["client_name"] = name
        state["step"] = "entering_phone"
        send(vk, peer_id, f"👤 Имя: {name}\n\nТеперь введите ваш номер телефона:")
        return

    if step == "entering_phone":
        phone = text.strip()
        if len(phone) < 7:
            send(vk, peer_id, "Пожалуйста, введите корректный номер телефона:")
            return
        finish_booking(vk, peer_id, user_id, phone)
        return

    if lowered in ("начать", "start", "привет", "меню", "hello", "/start", "в меню"):
        clear_state(user_id)
        show_main(vk, peer_id)
        return

    if lowered in ("записаться", "назад"):
        if lowered == "назад" and step == "choosing_service":
            show_main(vk, peer_id)
            return
        state["step"] = "choosing_service"
        state["data"] = {}
        send(vk, peer_id, "💅 Выберите услугу:", services_kb())
        return

    if lowered == "услуги":
        show_services(vk, peer_id)
        return

    if lowered == "контакты":
        show_contacts(vk, peer_id)
        return

    if lowered == "как записаться":
        show_howto(vk, peer_id)
        return

    if step == "choosing_service":
        for key, service in SERVICES.items():
            if text.strip() == service["name"]:
                state["step"] = "choosing_time"
                state["data"] = {
                    "service_key": key,
                    "service_name": service["name"],
                }
                send(
                    vk,
                    peer_id,
                    f"✅ Услуга: {service['name']} ({service['price']})\n\n🕐 Выберите удобное время:",
                    time_kb(),
                )
                return
        send(vk, peer_id, "Выберите услугу из кнопок:", services_kb())
        return

    if step == "choosing_time":
        if lowered == "назад":
            state["step"] = "choosing_service"
            send(vk, peer_id, "💅 Выберите услугу:", services_kb())
            return
        if text.strip() in TIME_SLOTS:
            state["step"] = "entering_name"
            state["data"]["time_slot"] = text.strip()
            send(vk, peer_id, f"🕐 Время: {text.strip()}\n\nВведите ваше имя:")
            return
        send(vk, peer_id, "Выберите время из кнопок:", time_kb())
        return

    show_main(vk, peer_id)


def ack_event(vk, event) -> None:
    try:
        vk.messages.sendMessageEventAnswer(
            event_id=event.object.event_id,
            user_id=event.object.user_id,
            peer_id=event.object.peer_id,
        )
    except Exception as exc:
        logger.debug("Event ack: %s", exc)


def get_group_info(vk) -> dict:
    result = vk.groups.getById(group_id=VK_GROUP_ID)
    if isinstance(result, dict) and "groups" in result:
        return result["groups"][0]
    if isinstance(result, list) and result:
        return result[0]
    raise RuntimeError(f"Неожиданный ответ VK API: {result!r}")


def check_setup(vk) -> None:
    """Проверка токена и группы перед запуском."""
    try:
        info = get_group_info(vk)
    except vk_api.exceptions.ApiError as exc:
        raise SystemExit(
            f"❌ VK API ошибка [{exc.code}]: {exc}\n"
            f"Проверь VK_TOKEN и VK_GROUP_ID={VK_GROUP_ID}"
        ) from exc
    except Exception as exc:
        raise SystemExit(
            f"❌ Не удалось получить данные группы: {exc}\n"
            f"Проверь VK_TOKEN и VK_GROUP_ID={VK_GROUP_ID}"
        ) from exc

    name = info.get("name", "")
    if name.upper() == "DELETED":
        raise SystemExit(
            "❌ Группа ВК удалена или недоступна.\n\n"
            "Что сделать:\n"
            "1. Создай новое сообщество (Частное)\n"
            "2. Включи Сообщения + Long Poll API\n"
            "3. Создай новый ключ доступа\n"
            "4. Обнови только bots/vk-salon-booking/.env"
        )

    try:
        vk.groups.getLongPollServer(group_id=VK_GROUP_ID)
    except vk_api.exceptions.ApiError as exc:
        if exc.code == 15:
            raise SystemExit(
                "❌ Access denied — Long Poll не доступен.\n\n"
                "Проверь в группе:\n"
                "• Управление → Работа с API → Long Poll API → ВКЛ\n"
                "• Сообщения → Сообщения сообщества → ВКЛ\n"
                "• Ключ: права «Управление сообществом» + «Сообщения»\n"
                "• Если не помогло — удали ключ и создай новый"
            ) from exc
        raise

    logger.info("Группа «%s» — Long Poll OK", name)
    logger.info(
        "Если кнопки не работают: Сообщения → Настройки для бота → "
        "«Возможности ботов» → ВКЛ"
    )


def listen_loop(vk, longpoll) -> None:
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                message = event.object.message
                user_id = message["from_id"]
                peer_id = message["peer_id"]
                text = (message.get("text") or "").strip()
                logger.info("Событие MESSAGE_NEW peer=%s user=%s", peer_id, user_id)

                if text:
                    handle_text(vk, user_id, peer_id, text)
                else:
                    show_main(vk, peer_id)

            elif event.type == VkBotEventType.MESSAGE_EVENT:
                ack_event(vk, event)
                payload = event.object.payload or {}
                if isinstance(payload, str):
                    payload = json.loads(payload)
                handle_payload(
                    vk,
                    event.object.user_id,
                    event.object.peer_id,
                    payload,
                )

        except Exception:
            logger.exception("Ошибка обработки события")


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"VK bot is running")

    def log_message(self, *_args) -> None:
        pass


def start_health_server(port: int) -> None:
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    logger.info("Health server on port %s", port)
    server.serve_forever()


def main() -> None:
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    check_setup(vk)
    longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)

    if os.getenv("PORT"):
        port = int(os.environ["PORT"])
        threading.Thread(target=start_health_server, args=(port,), daemon=True).start()
        threading.Thread(target=listen_loop, args=(vk, longpoll), daemon=True).start()
        logger.info("VK-бот на Render (группа %s)", VK_GROUP_ID)
        import time
        while True:
            time.sleep(3600)
    else:
        logger.info("VK-бот локально (группа %s) — пиши «привет» в группу", VK_GROUP_ID)
        listen_loop(vk, longpoll)


if __name__ == "__main__":
    main()
