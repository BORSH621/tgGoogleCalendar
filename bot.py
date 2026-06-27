import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
import calendar_service as cal

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


class AuthStates(StatesGroup):
    waiting_for_code = State()


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    db.init_db()
    user_id = message.from_user.id
    user_data = db.get_user(user_id)

    if user_data and user_data[1]:
        await message.answer("Вы уже авторизованы! Бот отслеживает ваши встречи.\n"
                             "Изменить время уведомлений: `/set_reminder <минуты>`\n"
                             "Посмотреть историю: `/history` (ввод командами)", parse_mode="Markdown")
        return

    try:
        flow = cal.get_auth_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')

        await state.update_data(code_verifier=getattr(flow, 'code_verifier', None))

        await message.answer(
            f"Привет! Для работы мне нужен доступ к твоему Google Календарю.\n\n"
            f"1. Перейди по [ссылке для авторизации]({auth_url})\n"
            f"2. Войди в аккаунт и разреши доступ.\n"
            f"3. Тебя перенаправит на пустую страницу (`http://localhost/...`).\n"
            f"4. **Скопируй всю эту ссылку целиком** из адресной строки браузера и отправь её мне сюда.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        await state.set_state(AuthStates.waiting_for_code)
    except Exception as e:
        logging.error(f"Ошибка генерации OAuth ссылки: {e}")
        await message.answer("Произошла ошибка при запуске авторизации. Проверьте конфигурацию client_secrets.json.")


@dp.message(AuthStates.waiting_for_code)
async def process_auth_code(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_input = message.text.strip()

    try:
        state_data = await state.get_data()
        saved_verifier = state_data.get("code_verifier")

        flow = cal.get_auth_flow()

        if saved_verifier:
            flow.code_verifier = saved_verifier

        if user_input.startswith("http"):
            flow.fetch_token(authorization_response=user_input)
        else:
            flow.fetch_token(code=user_input)

        creds = flow.credentials

        db.save_user_credentials(user_id, creds.to_json())
        await message.answer(
            "🎉 Авторизация успешна! Теперь я присылаю уведомления за 15 минут до встреч (по умолчанию).")
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка валидации OAuth токена: {e}")
        await message.answer(
            "Не удалось подтвердить код. Убедитесь, что скопировали ссылку или код верно, и попробуйте /start снова.")
        await state.clear()


@dp.message(Command("set_reminder"))
async def cmd_set_reminder(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование команды: `/set_reminder <минуты>`\nПример: `/set_reminder 15`",
                             parse_mode="Markdown")
        return

    minutes = int(args[1])
    db.update_reminder(user_id, minutes)
    await message.answer(
        f"⏰ Время напоминания изменено! Теперь вы получите уведомление за *{minutes} минут* до начала встречи.",
        parse_mode="Markdown")


@dp.message(Command("history"))
async def cmd_history(message: Message):
    user_id = message.from_user.id
    history_items = db.get_history(user_id)

    if not history_items:
        user_data = db.get_user(user_id)
        if user_data and user_data[1]:
            past_events = cal.check_past_events(user_data[1])
            for event in past_events:
                title = event.get('summary', 'Без названия')
                end_time_raw = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
                if end_time_raw:
                    dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
                    db.add_to_history(user_id, title, dt.strftime("%d.%m.%Y %H:%M"))
            history_items = db.get_history(user_id)

    if not history_items:
        await message.answer("История встреч пуста.")
        return

    response = "📋 *Последние 10 встреч:*\n\n"
    for idx, (title, end_time) in enumerate(history_items, 1):
        response += f"{idx}. [{end_time}] {title}\n"

    await message.answer(response, parse_mode="Markdown")


async def check_calendars_job():
    logging.info("Фоновая проверка календарей запущена...")
    users = db.get_all_authenticated_users()

    for user_id, reminder_minutes, creds_json in users:
        events, updated_creds = cal.get_upcoming_events(creds_json, minutes_ahead=reminder_minutes + 5)

        if updated_creds:
            db.save_user_credentials(user_id, updated_creds)

        for event in events:
            event_id = event.get('id')
            if db.is_reminder_sent(user_id, event_id):
                continue

            start_time_raw = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if not start_time_raw:
                continue

            start_time = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
            now = datetime.now(start_time.tzinfo)
            time_delta = start_time - now

            if time_delta.total_seconds() <= (reminder_minutes * 60) and time_delta.total_seconds() > 0:
                title = event.get('summary', 'Без названия')
                link = event.get('htmlLink', '')
                hangout_link = event.get('hangoutLink', '')

                final_link = hangout_link if hangout_link else link
                display_time = start_time.strftime("%d %B %Y, %H:%M")

                msg_text = (
                    f"⏰ *Напоминание!*\n\n"
                    f"Встреча:\n\"{title}\"\n\n"
                    f"Время: {display_time}\n"
                    f"Ссылка: [Перейти]({final_link})"
                )

                try:
                    await bot.send_message(chat_id=user_id, text=msg_text, parse_mode="Markdown",
                                           disable_web_page_preview=True)
                    db.mark_reminder_as_sent(user_id, event_id)
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

        past_events = cal.check_past_events(creds_json)
        for event in past_events:
            end_time_raw = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            if end_time_raw:
                end_dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
                title = event.get('summary', 'Без названия')
                db.add_to_history(user_id, title, end_dt.strftime("%d.%m.%Y %H:%M"))


async def main():
    db.init_db()
    scheduler.add_job(check_calendars_job, "interval", minutes=5)
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())