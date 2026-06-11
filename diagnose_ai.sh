#!/bin/bash

# Скрипт для диагностики проблемы с Ollama и AI помощником
# Использование: bash diagnose_ai.sh

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🔧 ДИАГНОСТИКА OLLAMA И AI ПОМОЩНИКА                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ ОШИБКА${NC}"
    fi
}

# Функция для проверки наличия команды
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Проверка Docker
echo -e "\n${BLUE}1️⃣  Проверка Docker...${NC}"
if command_exists docker; then
    echo -n "   Docker установлен: "
    docker --version
    echo -e "   ${GREEN}✅ Docker доступен${NC}"
else
    echo -e "   ${RED}❌ Docker не установлен${NC}"
    exit 1
fi

# 2. Проверка контейнеров
echo -e "\n${BLUE}2️⃣  Проверка контейнеров...${NC}"

echo -n "   metal_backend: "
if docker ps | grep -q metal_backend; then
    echo -e "${GREEN}✅ Запущен${NC}"
else
    echo -e "${RED}❌ Не запущен или не найден${NC}"
    echo "      Попробуйте: docker-compose up -d"
fi

echo -n "   metal_frontend: "
if docker ps | grep -q metal_frontend; then
    echo -e "${GREEN}✅ Запущен${NC}"
else
    echo -e "${RED}❌ Не запущен или не найден${NC}"
fi

echo -n "   metal_db (PostgreSQL): "
if docker ps | grep -q metal_db; then
    echo -e "${GREEN}✅ Запущен${NC}"
else
    echo -e "${RED}❌ Не запущен или не найден${NC}"
fi

echo ""
echo "   ℹ️  Ollama запущен локально (не в Docker контейнере)"

# 3. Проверка памяти контейнеров Docker
echo -e "\n${BLUE}3️⃣  Проверка использования памяти Docker контейнеров...${NC}"

docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" | grep -E "backend|frontend|db" || echo "   ℹ️  Контейнеры не запущены"

echo ""
echo "   ℹ️  Ollama запущен локально, на ноутбуке"

# 4. Проверка доступности локального Ollama
echo -e "\n${BLUE}4️⃣  Проверка локального Ollama API (http://localhost:11434)...${NC}"
echo -n "   Доступность http://localhost:11434/api/tags: "
if curl -s -f http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Доступно${NC}"
    echo "   Загруженные модели:"
    curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/     /' || echo "     (не удалось получить список)"
else
    echo -e "${RED}❌ Недоступно${NC}"
    echo "      Убедитесь, что Ollama запущен локально:"
    echo "      ollama serve"
fi

# 5. Проверка Backend Health
echo -e "\n${BLUE}5️⃣  Проверка Backend...${NC}"
echo -n "   Health Check (http://localhost:5111/health): "
if curl -s -f http://localhost:5111/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Здоров${NC}"
else
    echo -e "${RED}❌ Не здоров${NC}"
fi

echo -n "   AI Health Check (http://localhost:5111/api/ai-health): "
if curl -s -f http://localhost:5111/api/ai-health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ AI доступен${NC}"
    curl -s http://localhost:5111/api/ai-health | grep -o '"status":"[^"]*"'
else
    echo -e "${RED}❌ AI недоступен${NC}"
fi

# 6. Проверка Frontend
echo -e "\n${BLUE}6️⃣  Проверка Frontend...${NC}"
echo -n "   Frontend (http://localhost:8081): "
if curl -s -f http://localhost:8081/index.html >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Доступен${NC}"
else
    echo -e "${RED}❌ Недоступен${NC}"
fi

# 7. Проверка логов
echo -e "\n${BLUE}7️⃣  Последние ошибки в логах Docker контейнеров...${NC}"
if docker logs metal_backend 2>&1 | tail -20 | grep -i -E "error|fail|connection"; then
    echo "   ⚠️  Обнаружены ошибки в логах Backend"
else
    echo "   ✅ Явных ошибок в Backend не обнаружено"
fi

# Итоги
echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📋 ИТОГИ ДИАГНОСТИКИ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

OLLAMA_OK=0
BACKEND_OK=0
FRONTEND_OK=0

curl -s -f http://localhost:11434/api/tags >/dev/null 2>&1 && OLLAMA_OK=1
curl -s -f http://localhost:5111/health >/dev/null 2>&1 && BACKEND_OK=1
curl -s -f http://localhost:8081/index.html >/dev/null 2>&1 && FRONTEND_OK=1

echo ""
if [ $OLLAMA_OK -eq 1 ] && [ $BACKEND_OK -eq 1 ] && [ $FRONTEND_OK -eq 1 ]; then
    echo -e "${GREEN}✅ ВСЕ СЕРВИСЫ РАБОТАЮТ КОРРЕКТНО!${NC}"
    echo ""
    echo "Попробуйте:"
    echo "  1. Откройте http://localhost:8081"
    echo "  2. Нажмите кнопку CPM AI"
    echo "  3. Отправьте сообщение"
else
    echo -e "${YELLOW}⚠️  НЕКОТОРЫЕ СЕРВИСЫ НЕ РАБОТАЮТ${NC}"
    echo ""
    
    if [ $OLLAMA_OK -eq 0 ]; then
        echo "   Ollama недоступен на http://localhost:11434:"
        echo "   - Убедитесь, что Ollama запущен локально"
        echo "   - Выполните: ollama serve"
        echo "   - Проверьте, что модель загружена: ollama list"
    fi
    
    if [ $BACKEND_OK -eq 0 ]; then
        echo "   Backend не отвечает:"
        echo "   - Проверьте, запущен ли контейнер: docker ps"
        echo "   - Смотрите логи: docker logs metal_backend"
    fi
    
    if [ $FRONTEND_OK -eq 0 ]; then
        echo "   Frontend не доступен:"
        echo "   - Проверьте, запущен ли nginx контейнер"
        echo "   - Смотрите логи: docker logs metal_frontend"
    fi
fi

echo ""
echo -e "${BLUE}📚 Для подробной информации смотрите: LOCAL_OLLAMA_SETUP.md${NC}"
