# Многофункциональный бот

 * Создание кружков (длительность видео не ограничена)
 * Скачивание с TikTok+распознавание песни
 * Скачивание с Instagram Reels
 * Извлечение аудио из tt/reels
 * Скачивание с YouTube
 * Скачивание с Pornhub


#ИНСТРУКЦИЯ
1) вам потребуется Termux c F-droid
2) установка Ubuntu (я использую от этого разработчика jorexdeveloper)
```pkg update -y && pkg upgrade -y && pkg install -y curl && curl -fsSLO https://raw.githubusercontent.com/jorexdeveloper/termux-ubuntu/main/install-ubuntu.sh && bash install-ubuntu.sh```
это установит автоматические Proot Ubuntu запустите командой ub

3) вам потребуется установить такой пакет для установки python3.11
```sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev git```

4) создайте виртуальную среду (venv)
например:
```mkdir my_bot && cd my_bot```

5) создать venv
```python3.11 -m venv venv```

6) активация
```source venv/bin/activate```

7) установка зависимости 
```pip install -r requirements.txt```

8) запуск бота
```poetry install poetry run python main.py```

а при следующем запуске
```poetry run python main.py```



