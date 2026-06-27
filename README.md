# tgGoogleCalendar

Асинхронный Telegram-бот на базе `Aiogram 3` для интеграции с Google Calendar API. Бот циклично проверяет календарь пользователя, отслеживает его расписание и автоматически отправляет напоминания о предстоящих встречах прямо в чат Telegram.

---

## 🛠 Технический стек и требования

* **Язык программирования:** Python 3.10+
* **Основные библиотеки:** `aiogram` (3.x), `apscheduler`, `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`, `PySocks`
* **База данных:** SQLite

### Чистая структура репозитория на GitHub:
```text
tgGoogleCalendar/
│
├── bot.py                # Главный файл запуска бота и обработки команд пользователя
├── calendar_service.py   # Логика авторизации OAuth 2.0 и запросов к Google Calendar API
├── database.py           # Инициализация базы данных SQLite и методы работы с пользователями
├── requirements.txt      # Список зависимостей для быстрой установки на новом устройстве
├── .gitignore            # Файл исключений
└── README.md             # Текущая инструкция к проекту

Активируйте виртуальное окружение в зависимости от вашей ОС:

Windows (PowerShell): .\venv\Scripts\Activate.ps1
Windows (CMD / Командная строка): .\venv\Scripts\activate.bat
Linux / macOS: source venv/bin/activate

Установите все необходимые библиотеки: pip install -r requirements.txt

Создайте в корневой папке проекта текстовый файл с именем .env и вставьте туда токен вашего Telegram-бота

Файл client_secrets.json
1) Перейдите в консоль разработчика Google Cloud Console.
2) Откройте раздел APIs & Services -> Library, найдите Google Calendar API и нажмите кнопку Enable.
3) Перейдите на вкладку OAuth consent screen:
  Настройте тип согласия как External.
  Заполните обязательные поля.
  В блоке Publishing status обязательно нажмите кнопку Publish App. Это переведет проект из режима тестирования в рабочий режим и позволит авторизоваться любому пользователю без ручного внесения в списки тестировщиков.

4) Перейдите во вкладку Credentials:
  Нажмите кнопку + Create Credentials -> OAuth client ID.
  Выберите тип приложения: Desktop app.

5)Нажмите Create, скачайте полученный файл в формате JSON, переименуйте его строго в client_secrets.json и положите в корень папки проекта.

Убедитесь, что ваше venv активно, и запустите бота стандартной командой: python bot.py
