# ⚡ НЕМЕДЛЕННО: Как начать работу с локальным Ollama

## 📌 ВАЖНО: Минимум действий для запуска

### Шаг 1️⃣: Запустить Ollama на ноутбуке (1 команда)
```bash
ollama serve
```
Оставьте этот терминал открытым!

### Шаг 2️⃣: Загрузить модель (в новом терминале)
```bash
ollama pull qwen2.5:7b
```

### Шаг 3️⃣: Перезагрузить Docker (3 команды)
```bash
cd /home/ranil/Рабочий\ стол/PROJECT
docker-compose down
docker-compose up -d
```

### Шаг 4️⃣: Проверить (откройте браузер)
```
http://localhost:8081
```

---

## ✅ Проверка

```bash
# Проверить Ollama доступен
curl http://localhost:11434/api/tags

# Проверить Backend видит Ollama
curl http://localhost:5111/api/ai-health
```

Если оба работают - можете писать сообщения в CPM AI чат! 🚀

---

## 🐛 Если на Linux и не работает

Замените в `docker-compose.yml`:
```yaml
OLLAMA_URL: http://host.docker.internal:11434
```
На:
```yaml
OLLAMA_URL: http://192.168.1.100:11434  # Замените на ваш IP адрес машины
```

Перезагрузите:
```bash
docker-compose down
docker-compose up -d
```

---

## 📚 Полная документация

- **LOCAL_OLLAMA_SETUP.md** - полная инструкция для всех ОС
- **LOCAL_OLLAMA_MIGRATION.md** - что изменилось и почему
- **diagnose_ai.sh** - диагностический скрипт

---

## 🎯 Готово!

Теперь Ollama на вашем ноутбуке, а Docker контейнеры подключаются к нему.

**Дельта памяти:**
- ❌ Было: Docker требовал 5GB памяти для Ollama
- ✅ Теперь: Docker требует ~800MB, Ollama использует вашу реальную память

Наслаждайтесь! 🎉
