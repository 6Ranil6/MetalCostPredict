let currentMode = 'manual'; // ручной ввод или загрузка файла
let fieldOptions = {}; // кэш для значений из field_options.json

// API URL - использует относительный путь для Nginx проксирования
const API_URL = '/api';
// Для локального запуска без docker раскомментируйте:
// const API_URL = 'http://localhost:5111/api';

function renderUserStatus() {
    const container = document.querySelector('.container');
    if (!container) return;

    // очищаем старую панель статуса, если она была отрендерена ранее
    const oldPanel = document.getElementById('user-status-panel');
    if (oldPanel) oldPanel.remove();

    const user = JSON.parse(localStorage.getItem('user'));
    
    const panel = document.createElement('div');
    panel.id = 'user-status-panel';
    panel.style.display = 'flex';
    panel.style.justifyContent = 'space-between';
    panel.style.alignItems = 'center';
    panel.style.padding = '0.8rem 1.5rem';
    panel.style.background = '#fff0e0';
    panel.style.borderRadius = '1rem';
    panel.style.marginBottom = '1.5rem';
    panel.style.fontSize = '0.95rem';
    panel.style.border = '1px solid rgba(255, 123, 0, 0.2)';

    if (user) {
        let roleBadge = user.role === 'pro' ? 'Pro' : user.role === 'admin' ? 'Admin' : 'Пользователь';
        panel.innerHTML = `
            <span>Вы вошли как: <strong>${user.name}</strong> (${roleBadge})</span>
            <button onclick="handleLogout()" style="background: none; border: none; color: var(--primary); font-weight: bold; cursor: pointer;">Выйти</button>
        `;
    } else {
        panel.innerHTML = `
            <span>Вы используете калькулятор в режиме гостя.</span>
            <a href="auth.html" style="color: var(--primary); font-weight: bold; text-decoration: none;">Войти в личный кабинет</a>
        `;
    }

    // втавляем панель в начало контейнера перед первой карточкой или кнопкой назад
    const referenceElement = container.querySelector('.card, .back-btn');
    if (referenceElement) {
        container.insertBefore(panel, referenceElement);
    }
}

// выход из личного кабинета
function handleLogout() {
    localStorage.removeItem('user');
    renderUserStatus();
    updateNavButtonsAccess();
    
    // если пользователь вышел, находясь на странице личного кабинета - перезагружаем форму
    if (document.getElementById('login-form')) {
        window.location.reload();
    } else {
        // иначе перенаправляем на главную
        window.location.href = 'index.html';
    }
}

// функция для контроля доступности кнопок на главной странице
function updateNavButtonsAccess() {
    const user = JSON.parse(localStorage.getItem('user'));
    const navCards = document.querySelectorAll('a.nav-card');
    
    navCards.forEach(card => {
        const href = card.getAttribute('href');
        
        if (href === 'auth.html') {
            if (user) {
                // пользователь авторизован - кнопка "Личный кабинет" неактивна
                card.style.pointerEvents = 'none';
                card.style.opacity = '0.5';
                card.style.cursor = 'not-allowed';
                card.title = 'Вы уже авторизованы';
                card.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    alert('Вы уже вошли в систему. Используйте кнопку "Выйти" в панели профиля.');
                    return false;
                };
            } else {
                // пользователь не авторизован - кнопка активна
                card.style.pointerEvents = 'auto';
                card.style.opacity = '1';
                card.style.cursor = 'pointer';
                card.title = '';
                card.onclick = null;
            }
        } else if (href === 'calc.html' || href === 'feedback.html') {
            if (!user) {
                // пользователь не авторизован - делаем кнопки неактивными
                card.style.pointerEvents = 'none';
                card.style.opacity = '0.5';
                card.style.cursor = 'not-allowed';
                card.title = 'Требуется авторизация';
                card.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const actionText = href === 'calc.html' ? 'доступа к калькулятору' : 'отправки обратной связи';
                    alert(`Для ${actionText} необходимо войти или зарегистрироваться.`);
                    window.location.href = 'auth.html';
                    return false;
                };
            } else {
                // пользователь авторизован - кнопки активны
                card.style.pointerEvents = 'auto';
                card.style.opacity = '1';
                card.style.cursor = 'pointer';
                card.title = '';
                card.onclick = null;
            }
        }
    });
}

// инициализация при загрузке документа
document.addEventListener('DOMContentLoaded', () => {
    loadFieldOptions(); // загружаем значения для dropdown селектов
    renderUserStatus();
    
    // обновляем доступность кнопок на главной странице
    updateNavButtonsAccess();
    
    // автоматическое заполнение имени и почты на странице обратной связи для авторизованных пользователей
    const user = JSON.parse(localStorage.getItem('user'));
    const fbName = document.getElementById('feedback-name');
    const fbEmail = document.getElementById('feedback-email');
    if (user && fbName && fbEmail) {
        fbName.value = user.name;
        fbEmail.value = user.email;
    }
    
    // Показываем раздел истории и загружаем её для авторизованных пользователей
    if (user && document.getElementById('history-section')) {
        document.getElementById('history-section').style.display = 'block';
        loadPredictionsHistory();
        setupHistoryFilterListeners();
    }
    
    // инициализируем слушатели для контроля доступности кнопок
    setupFieldListeners();
    
    // инициализируем состояние кнопки
    updateCalculateButtonState();
});


function setMode(mode) { // устанавливаем тип ввода
    currentMode = mode;
    
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
    if (event && event.target) {
        event.target.classList.add('active');
    }

    const manualSection = document.getElementById('manual-section');
    const fileSection = document.getElementById('file-section');
    const resultBox = document.getElementById('result');

    if (manualSection && fileSection) {
        if (mode === 'manual') {
            manualSection.classList.remove('hidden');
            fileSection.classList.add('hidden');
        } else {
            manualSection.classList.add('hidden');
            fileSection.classList.remove('hidden');
        }
    }
    if (resultBox) {
        resultBox.style.display = 'none';
    }
    
    // обновляем состояние кнопки при переключении режима
    updateCalculateButtonState();
}

// функция для проверки доступности кнопки "рассчитать"
function updateCalculateButtonState() {
    const btn = document.querySelector('.calculate-btn');
    if (!btn) return;

    if (currentMode === 'manual') {
        const categoryPrice = document.getElementById('categoryPrice').value;
        btn.disabled = !categoryPrice;
    } else {
        const fileInput = document.getElementById('file-input');
        btn.disabled = !fileInput || !fileInput.files || fileInput.files.length === 0;
    }
}

// добавляем слушатели на изменение критичных полей
function setupFieldListeners() {
    const categoryPrice = document.getElementById('categoryPrice');
    const fileInput = document.getElementById('file-input');

    if (categoryPrice) {
        categoryPrice.addEventListener('change', updateCalculateButtonState);
    }

    if (fileInput) {
        fileInput.addEventListener('change', updateCalculateButtonState);
    }
}

function handleFile(input) { // показываем название выбранного файла
    const fileNameDisplay = document.getElementById('file-name');
    if (fileNameDisplay && input.files && input.files[0]) {
        const file = input.files[0];
        const maxSize = 5 * 1024 * 1024; // 5MB

        if (file.size > maxSize) {
            showInfoModal(`Файл слишком большой (${(file.size / 1024 / 1024).toFixed(2)} МБ). Максимальный размер — 5 МБ.`, "Ошибка файла");
            input.value = ""; // Сбрасываем выбор
            fileNameDisplay.textContent = "";
            updateCalculateButtonState();
            return;
        }

        fileNameDisplay.textContent = file.name;
    }
}

async function calculate() {
    const btn = document.querySelector('.calculate-btn');
    const resultBox = document.getElementById('result');
    const priceDisplay = document.getElementById('price-display');

    if (!btn || !resultBox || !priceDisplay) return;

    btn.textContent = "Считаем...";
    btn.disabled = true;

    // считываем id авторизованного пользователя для логирования истории расчетов
    const user = JSON.parse(localStorage.getItem('user'));
    const userId = user ? user.id : null;

    try {
        let response;

        if (currentMode === 'manual') {
            // проверяем, что категория цены выбрана ТОЛЬКО для ручного ввода
            const categoryPrice = document.getElementById('categoryPrice').value;
            if (!categoryPrice) {
                showInfoModal('Пожалуйста, выберите категорию цены из списка', 'Внимание');
                btn.textContent = "Рассчитать стоимость";
                btn.disabled = false;
                return;
            }

            const formData = {
                'user_id': userId, // передается на бэкенд для привязки к predictions_history
                'Наименование': document.getElementById('name').value,
                'Категория_цены': categoryPrice,
                'Основная_марка': document.getElementById('mainBrand').value,
                'Марка': document.getElementById('brand').value,
                'Тип_материала': document.getElementById('materialType').value,
                'Тип_продукции': document.getElementById('productType').value,
                'Размер_A': document.getElementById('sizeA').value,
                'Размер_B': document.getElementById('sizeB').value,
                'Размер_C': document.getElementById('sizeC').value,
                'Толщина': document.getElementById('thickness').value,
                'Типоразмер': document.getElementById('typeSize').value,
                'Тип_стандарта': document.getElementById('standardType').value,
                'Номер_стандарта': document.getElementById('standardNumber').value,
                'Условие_цены': document.getElementById('priceCondition').value
            };

            response = await fetch(`${API_URL}/predict-manual`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка сервера при расчете');
            }

            const result = await response.json();
            priceDisplay.textContent = result.price.toLocaleString('ru-RU') + " " + categoryPrice;
            
            // Обновляем историю после успешного расчета
            if (userId) {
                loadPredictionsHistory();
            }
        } else {
            const fileInput = document.getElementById('file-input');
            if (!fileInput || !fileInput.files[0]) {
                showInfoModal("Пожалуйста, выберите файл перед отправкой.", "Внимание");
                btn.textContent = "Рассчитать стоимость";
                btn.disabled = false;
                return;
            }
            
            const fileData = new FormData();
            fileData.append('file', fileInput.files[0]);
            fileData.append('user_id', userId);

            response = await fetch(`${API_URL}/predict-file`, {
                method: 'POST',
                body: fileData 
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка при обработке файла');
            }

            const blob = await response.blob(); 
            const url = window.URL.createObjectURL(blob); 
            const a = document.createElement('a'); 
            a.href = url; 
            a.download = "result_prices.csv";
            document.body.appendChild(a); 
            a.click(); 
            a.remove();
            
            priceDisplay.textContent = "Файл обработан и скачан!";
            
            // Обновляем историю после успешной загрузки файла
            if (userId) {
                loadPredictionsHistory();
            }
        }
        
        resultBox.style.display = 'block';

    } catch (error) {
        console.error("Ошибка запроса:", error);
        showInfoModal(error.message || "Произошла непредвиденная ошибка. Проверьте соединение с бэкендом.", "Ошибка расчета");
    } finally {
        btn.textContent = "Рассчитать стоимость";
        btn.disabled = false;
    }
}


function toggleAuthMode(mode) { // переключение вкладок вход / регистрация в ЛК
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');

    if (!loginForm || !registerForm || !tabLogin || !tabRegister) return;

    if (mode === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabLogin.classList.remove('active');
        tabRegister.classList.add('active');
    }
}

async function handleAuthSubmit(event, type) {
    event.preventDefault();
    const inputs = event.target.querySelectorAll('input');
    
    try {
        if (type === 'login') {
            const email = inputs[0].value;
            const password = inputs[1].value;
            
            const response = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Неверный адрес почты или пароль');
            }
            
            // сохраняем сессию в localStorage
            localStorage.setItem('user', JSON.stringify(data));
            
            // обновляем состояние доступа к кнопкам
            updateNavButtonsAccess();
            
            // переадресовываем на главную
            window.location.href = "index.html";
        } else {
            const name = inputs[0].value;
            const email = inputs[1].value;
            const password = inputs[2].value;
            const confirmPassword = inputs[3].value;
            
            if (password !== confirmPassword) {
                showInfoModal("Введенные пароли не совпадают!", "Ошибка регистрации");
                return;
            }
            
            const response = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Не удалось зарегистрироваться');
            }
            
            toggleAuthMode('login');
        }
        event.target.reset();
    } catch (error) {
        console.error("Ошибка аутентификации:", error);
        showInfoModal(error.message, "Ошибка аутентификации");
    }
}

async function handleFeedbackSubmit(event) {
    event.preventDefault();
    
    const user = JSON.parse(localStorage.getItem('user'));
    const userId = user ? user.id : null;

    const name = document.getElementById('feedback-name').value;
    const email = document.getElementById('feedback-email').value;
    const subject = document.getElementById('feedback-subject').value;
    const message = document.getElementById('feedback-message').value;

    const resultBox = document.getElementById('feedback-result');

    try {
        const response = await fetch(`${API_URL}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                name,
                email,
                subject,
                message
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка при отправке сообщения в поддержку');
        }

        if (resultBox) {
            resultBox.style.display = 'block';
            event.target.reset();
            
            // скрываем плашку успешной отправки через 6 секунд
            setTimeout(() => {
                resultBox.style.display = 'none';
            }, 6000);
        }
    } catch (error) {
        console.error("Ошибка отправки фидбека:", error);
        showInfoModal(error.message, "Ошибка отправки");
    }
}

// функция для загрузки истории предсказаний пользователя
async function loadPredictionsHistory() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return;

    const historyList = document.getElementById('history-list');
    const limitInput = document.getElementById('history-limit');
    if (!historyList || !limitInput) return;

    const limit = parseInt(limitInput.value) || 50;

    try {
        const response = await fetch(`${API_URL}/predictions-history/${user.id}?limit=${limit}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        
        if (!data || !data.history) {
            throw new Error('Некорректный формат ответа от сервера');
        }
        
        let history = data.history || [];
        
        // применяем фильтры
        history = applyHistoryFilters(history);

        if (history.length === 0) {
            historyList.innerHTML = '<p class="history-empty">История запросов пуста или не соответствует фильтрам</p>';
            return;
        }

        // формируем HTML для истории
        let historyHTML = '';
        history.forEach((item, index) => {
            try {
                const date = new Date(item.created_at).toLocaleString('ru-RU');
                const productName = (item.input_data && item.input_data['Наименование']) || 'Неизвестный продукт';
                const priceCategory = (item.input_data && item.input_data['Категория_цены']) || '₽';
                const price = item.predicted_price ? item.predicted_price.toLocaleString('ru-RU') : '0';

                historyHTML += `
                    <div class="history-item">
                        <div class="history-item-info">
                            <div class="history-item-name">${escapeHtml(productName)}</div>
                            <div class="history-item-date">${date}</div>
                        </div>
                        <div class="history-item-right">
                            <div class="history-item-price">${price} ${escapeHtml(priceCategory)}</div>
                            <div style="display: flex; gap: 0.3rem; margin-top: 0.3rem;">
                                <button class="history-item-btn" onclick="showHistoryDetails(${JSON.stringify(item.input_data).replace(/"/g, '&quot;')})">Подробно</button>
                                <button class="history-item-delete" onclick="deleteHistoryItem(${item.id})" title="Удалить из истории">❌</button>
                            </div>
                        </div>
                    </div>
                `;
            } catch (itemError) {
                console.error('Ошибка при обработке элемента истории:', itemError);
            }
        });

        historyList.innerHTML = historyHTML || '<p class="history-empty">Не удалось загрузить историю</p>';
    } catch (error) {
        console.error("Ошибка загрузки истории:", error);
        historyList.innerHTML = `<p class="history-empty" style="color: red;">Ошибка: ${error.message || 'неизвестная ошибка'}</p>`;
    }
}

// функция для применения фильтров к истории запросов
function applyHistoryFilters(history) {
    const searchInput = document.getElementById('history-search');
    const priceFilter = document.getElementById('history-price-filter');
    
    let filtered = history;
    
    // фильтр по поиску в названии
    if (searchInput && searchInput.value.trim()) {
        const searchText = searchInput.value.toLowerCase().trim();
        filtered = filtered.filter(item => {
            const productName = (item.input_data && item.input_data['Наименование']) || '';
            return productName.toLowerCase().includes(searchText);
        });
    }
    
    // фильтр по категории цены
    if (priceFilter && priceFilter.value) {
        const selectedPrice = priceFilter.value;
        filtered = filtered.filter(item => {
            const priceCategory = (item.input_data && item.input_data['Категория_цены']) || '';
            return priceCategory === selectedPrice;
        });
    }
    
    return filtered;
}

// Добавляем слушатели на фильтры при загрузке страницы
function setupHistoryFilterListeners() {
    const searchInput = document.getElementById('history-search');
    const priceFilter = document.getElementById('history-price-filter');
    const limitInput = document.getElementById('history-limit');
    
    if (searchInput) {
        searchInput.addEventListener('input', loadPredictionsHistory);
    }
    
    if (priceFilter) {
        priceFilter.addEventListener('change', loadPredictionsHistory);
    }
    
    if (limitInput) {
        limitInput.addEventListener('change', () => {
            const value = parseInt(limitInput.value);
            if (value > 5000) {
                showInfoModal('Мы сожалеем об ограничениях. Максимальное количество запросов для отображения - 5000. Вывести больше 5000 запросов нельзя.', 'Превышен лимит');
                limitInput.value = 5000;
            } else if (value < 0) {
                limitInput.value = 5;
            }
            loadPredictionsHistory();
        });
    }
}

// функция для очистки HTML от XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// функция для очистки отображения истории
function clearHistoryView() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return;

    showConfirmModal(
        'Вы уверены, что хотите очистить всю историю запросов?',
        () => clearAllHistory(user.id)
    );
}

// функция для очистки всей истории
async function clearAllHistory(userId) {
    try {
        const response = await fetch(`${API_URL}/hide-all-predictions/${userId}`, {
            method: 'POST'
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка при очистке истории');
        }

        const historyList = document.getElementById('history-list');
        if (historyList) {
            historyList.innerHTML = '<p class="history-empty">История запросов пуста</p>';
        }
        closeConfirmModal();
    } catch (error) {
        console.error("Ошибка очистки истории:", error);
        showInfoModal(`Ошибка: ${error.message}`, "Ошибка удаления");
    }
}

// функция для удаления одного элемента истории
async function deleteHistoryItem(predictionId) {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return;

    try {
        const response = await fetch(`http://127.0.0.1:5111/api/hide-prediction/${predictionId}/${user.id}`, {
            method: 'POST'
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка при удалении записи');
        }

        // перезагружаем историю
        loadPredictionsHistory();
    } catch (error) {
        console.error("Ошибка удаления записи:", error);
        showInfoModal(`Ошибка: ${error.message}`, "Ошибка удаления");
    }
}

// функция для показа подробной информации о запросе в модальном окне
function showHistoryDetails(inputData) {
    try {
        const modalBody = document.getElementById('modal-body');
        if (!modalBody) return;

        let detailsHTML = '';
        let hasData = false;

        for (const [key, value] of Object.entries(inputData || {})) {
            if (value !== null && value !== undefined && value !== 'отсутствует' && value !== '') {
                hasData = true;
                const displayValue = typeof value === 'number' ? value.toString() : String(value);
                detailsHTML += `
                    <div class="modal-body-item">
                        <div class="modal-body-label">${escapeHtml(key)}</div>
                        <div class="modal-body-value">${escapeHtml(displayValue)}</div>
                    </div>
                `;
            }
        }

        if (!hasData) {
            detailsHTML = '<p style="text-align: center; color: var(--text-muted);">Нет данных для отображения</p>';
        }

        modalBody.innerHTML = detailsHTML;

        // открываем модальное окно
        const modal = document.getElementById('details-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.style.display = 'flex';
        }
    } catch (error) {
        console.error('Ошибка при отображении деталей:', error);
        showInfoModal('Ошибка при загрузке деталей запроса', "Ошибка");
    }
}

// функция для закрытия модального окна подробной информации
function closeDetailsModal() {
    const modal = document.getElementById('details-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

// функция для показа информационного модального окна
function showInfoModal(message, title = 'Уведомление') {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content modal-confirm">
            <div class="modal-header">
                <h2>${escapeHtml(title)}</h2>
            </div>
            <div class="modal-body">
                <p>${escapeHtml(message)}</p>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Закрыть</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// переменная для сохранения callback функции подтверждения
let confirmCallback = null;

// функция для показа модального окна подтверждения
function showConfirmModal(message, callback) {
    const confirmText = document.getElementById('confirm-text');
    if (confirmText) {
        confirmText.textContent = message;
    }
    confirmCallback = callback;

    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    }
}

// функция для закрытия модального окна подтверждения
function closeConfirmModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
    confirmCallback = null;
}

// функция для подтверждения действия
function confirmAction() {
    if (confirmCallback) {
        confirmCallback();
    }
    closeConfirmModal();
}

// закрытие модальных окон при клике на фон
document.addEventListener('click', function(event) {
    const detailsModal = document.getElementById('details-modal');
    const confirmModal = document.getElementById('confirm-modal');

    if (event.target === detailsModal && detailsModal) {
        closeDetailsModal();
    }
    if (event.target === confirmModal && confirmModal) {
        closeConfirmModal();
    }
});

// загрузка значений для dropdown
async function loadFieldOptions() {
    try {
        console.log('📍 Загрузка field_options.json...');
        const response = await fetch('/field_options.json');
        
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        
        fieldOptions = await response.json();
        console.log('field_options.json загружен:', fieldOptions);
        populateSelects();
    } catch (error) {
        console.error('✗ Ошибка при загрузке field_options.json:', error);
        console.error('⚠ Попытаюсь загрузить альтернативный путь...');
        // Пытаемся альтернативный путь
        try {
            const response = await fetch('./field_options.json');
            if (response.ok) {
                fieldOptions = await response.json();
                console.log('✓ field_options.json загружен (альтернативный путь):', fieldOptions);
                populateSelects();
            }
        } catch (altError) {
            console.error('✗ Не удалось загрузить field_options.json ни с одного пути:', altError);
        }
    }
}

// заполнение селектов значениями из field_options.json
function populateSelects() {
    const fieldMappings = {
        'materialType': 'Тип_материала',
        'productType': 'Тип_продукции',
        'standardType': 'Тип_стандарта',
        'priceCondition': 'Условие_цены'
    };

    for (const [elementId, fieldName] of Object.entries(fieldMappings)) {
        const element = document.getElementById(elementId);
        if (!element || !fieldOptions[fieldName]) continue;

        // очищаем элемент от старых опций
        while (element.options.length > 1) {
            element.remove(1);
        }

        // добавляем новые опции
        fieldOptions[fieldName].forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            element.appendChild(option);
        });
    }
    
    // инициализируем слушатели для двух независимых каскадов
    initializeCascadeListeners();
}

// инициализация слушателей для двух независимых каскадов
function initializeCascadeListeners() {
    // Каскад 1: Тип материала → Основная марка
    const materialTypeSelect = document.getElementById('materialType');
    if (materialTypeSelect) {
        materialTypeSelect.addEventListener('change', onMaterialTypeChange);
    }
    
    // Каскад 2: Тип продукции → Марка профиля
    const productTypeSelect = document.getElementById('productType');
    if (productTypeSelect) {
        productTypeSelect.addEventListener('change', onProductTypeChange);
    }
}

// Тип материала -> Основная марка
function onMaterialTypeChange() {
    const materialType = document.getElementById('materialType').value;
    const mainBrandGroup = document.getElementById('mainBrandGroup');
    const mainBrandSelect = document.getElementById('mainBrand');
    
    // очищаем выбор
    if (mainBrandSelect) mainBrandSelect.value = '';
    
    if (!materialType) {
        // если материал не выбран - скрываем поле
        if (mainBrandGroup) mainBrandGroup.style.display = 'none';
        clearMainBrandSelect();
        return;
    }
    
    // получаем список марок для выбранного материала
    const brands = fieldOptions.materialBrandsMap && fieldOptions.materialBrandsMap[materialType];
    
    if (!brands || brands.length === 0) {
        // если нет марок - скрываем поле
        if (mainBrandGroup) mainBrandGroup.style.display = 'none';
        clearMainBrandSelect();
        return;
    }
    
    // показываем и заполняем основную марку
    if (mainBrandGroup) mainBrandGroup.style.display = 'flex';
    fillMainBrandSelect(brands);
}

// Тип продукции -> Марка профиля
function onProductTypeChange() {
    const productType = document.getElementById('productType').value;
    const brandGroup = document.getElementById('brandGroup');
    const brandSelect = document.getElementById('brand');
    
    // очищаем выбор
    if (brandSelect) brandSelect.value = '';
    
    if (!productType) {
        // если тип не выбран - скрываем поле
        if (brandGroup) brandGroup.style.display = 'none';
        clearBrandSelect();
        return;
    }
    
    // получаем данные для выбранного типа продукции
    const productData = fieldOptions.productProfileBrandsMap && fieldOptions.productProfileBrandsMap[productType];
    
    if (!productData) {
        // если нет данных - скрываем поле
        if (brandGroup) brandGroup.style.display = 'none';
        clearBrandSelect();
        return;
    }
    
    // управляем видимостью марки профиля
    if (productData.hasProfileBrand) {
        if (brandGroup) brandGroup.style.display = 'flex';
        if (productData.profileBrands) {
            fillBrandSelect(productData.profileBrands);
        }
    } else {
        if (brandGroup) brandGroup.style.display = 'none';
        clearBrandSelect();
    }
}

// заполнение селекта основной марки (химический состав)
function fillMainBrandSelect(brands) {
    const select = document.getElementById('mainBrand');
    if (!select) return;
    
    // очищаем старые опции (кроме первой пустой)
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // добавляем новые опции
    brands.forEach(brand => {
        const option = document.createElement('option');
        option.value = brand;
        option.textContent = brand;
        select.appendChild(option);
    });
}

// заполнение селекта марки профиля (геометрия/форма)
function fillBrandSelect(brands) {
    const select = document.getElementById('brand');
    if (!select) return;
    
    // очищаем старые опции (кроме первой пустой)
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // добавляем новые опции
    brands.forEach(brand => {
        const option = document.createElement('option');
        option.value = brand;
        option.textContent = brand;
        select.appendChild(option);
    });
}

// очистка селекта основной марки
function clearMainBrandSelect() {
    const select = document.getElementById('mainBrand');
    if (select) {
        while (select.options.length > 1) {
            select.remove(1);
        }
    }
}

// очистка селекта марки профиля
function clearBrandSelect() {
    const select = document.getElementById('brand');
    if (select) {
        while (select.options.length > 1) {
            select.remove(1);
        }
    }
}

// Переменные для управления AI чатом
let aiChatState = {
    isOpen: false,
    currentSessionId: Date.now().toString(), // уникальный ID сессии
    messages: [],
    isLoading: false,
    selectedImage: null
};

// Инициализация AI чата при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initAIChatHandlers();
    // если нужно, генерируем новый session ID при загрузке
    if (!localStorage.getItem('aiSessionId')) {
        localStorage.setItem('aiSessionId', aiChatState.currentSessionId);
    } else {
        aiChatState.currentSessionId = localStorage.getItem('aiSessionId');
    }
});

function initAIChatHandlers() {
    const aiButton = document.getElementById('cpmAiButton');
    const aiModal = document.getElementById('aiChatModal');
    const aiCloseBtn = document.getElementById('aiChatCloseBtn');
    const aiSendBtn = document.getElementById('aiChatSendBtn');
    const aiInput = document.getElementById('aiChatInput');
    const aiImageUploadBtn = document.getElementById('aiImageUploadBtn');
    const aiImageInput = document.getElementById('aiImageInput');
    
    if (aiButton) {
        aiButton.addEventListener('click', toggleAIChatModal);
    }
    
    if (aiCloseBtn) {
        aiCloseBtn.addEventListener('click', closeAIChatModal);
    }
    
    if (aiSendBtn) {
        aiSendBtn.addEventListener('click', sendAIMessage);
    }
    
    if (aiInput) {
        aiInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendAIMessage();
            }
        });
        
        // автоматический рост textarea
        aiInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });
    }
    
    if (aiImageUploadBtn) {
        aiImageUploadBtn.addEventListener('click', function() {
            aiImageInput.click();
        });
    }
    
    if (aiImageInput) {
        aiImageInput.addEventListener('change', handleAIImageSelect);
    }
    
    // закрытие модального окна при клике вне его
    document.addEventListener('click', function(e) {
        if (aiModal && !aiModal.contains(e.target) && !aiButton.contains(e.target)) {
            // если модальное окно открыто, не закрываем его при клике вне
            // это опционально - можно удалить эту логику если хотите закрывать по клику вне
        }
    });
}

function toggleAIChatModal() {
    const aiModal = document.getElementById('aiChatModal');
    if (aiChatState.isOpen) {
        closeAIChatModal();
    } else {
        openAIChatModal();
    }
}

function openAIChatModal() {
    const aiModal = document.getElementById('aiChatModal');
    const aiMessages = document.getElementById('aiChatMessages');
    
    aiChatState.isOpen = true;
    aiModal.classList.add('active');
    
    // загружаем сохранённые сообщения если они есть
    if (aiChatState.messages.length === 0) {
        loadAIChatHistory();
    }
    
    // скролл вниз
    setTimeout(() => {
        aiMessages.scrollTop = aiMessages.scrollHeight;
    }, 100);
}

function closeAIChatModal() {
    const aiModal = document.getElementById('aiChatModal');
    aiChatState.isOpen = false;
    aiModal.classList.remove('active');
}

async function sendAIMessage() {
    const aiInput = document.getElementById('aiChatInput');
    const aiMessages = document.getElementById('aiChatMessages');
    const aiSendBtn = document.getElementById('aiChatSendBtn');
    
    const message = aiInput.value.trim();
    
    if (!message && !aiChatState.selectedImage) {
        return;
    }
    
    // отключаем кнопку отправки
    aiSendBtn.disabled = true;
    aiChatState.isLoading = true;
    
    // создаём элемент для индикатора загрузки
    let loadingEl = null;
    
    try {
        // добавляем сообщение пользователя в UI
        const userMessageEl = document.createElement('div');
        userMessageEl.className = 'ai-message user';
        userMessageEl.innerHTML = `
            <div class="ai-message-bubble user">${escapeHtml(message || '(изображение)')}</div>
        `;
        aiMessages.appendChild(userMessageEl);
        
        // если есть изображение, показываем его
        if (aiChatState.selectedImage) {
            const imageEl = document.createElement('img');
            imageEl.src = aiChatState.selectedImage;
            imageEl.style.maxWidth = '150px';
            imageEl.style.marginTop = '0.5rem';
            userMessageEl.querySelector('.ai-message-bubble').appendChild(imageEl);
        }
        
        // очищаем input и восстанавливаем высоту
        aiInput.value = '';
        aiInput.style.height = 'auto';
        
        // добавляем сообщение о загрузке
        loadingEl = document.createElement('div');
        loadingEl.className = 'ai-message';
        loadingEl.innerHTML = `
            <div class="ai-message-bubble assistant" style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="display: inline-block; width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; animation: pulse 1.5s infinite;"></span>
                Идёт загрузка ответа...
            </div>
        `;
        aiMessages.appendChild(loadingEl);
        
        // добавляем стиль для анимации пульсации
        if (!document.getElementById('loadingAnimation')) {
            const style = document.createElement('style');
            style.id = 'loadingAnimation';
            style.textContent = `
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `;
            document.head.appendChild(style);
        }
        
        // получаем текущего пользователя
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const userId = user.id || null;
        
        // отправляем сообщение на backend
        const response = await fetch(`${API_URL}/ai-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                message: message,
                user_id: userId,
                session_id: aiChatState.currentSessionId,
                image: aiChatState.selectedImage || null
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            // удаляем индикатор загрузки
            if (loadingEl && loadingEl.parentNode) {
                loadingEl.parentNode.removeChild(loadingEl);
            }
            
            throw new Error(error.error || 'Ошибка при отправке сообщения');
        }
        
        const data = await response.json();
        
        // удаляем индикатор загрузки
        if (loadingEl && loadingEl.parentNode) {
            loadingEl.parentNode.removeChild(loadingEl);
        }
        
        // добавляем ответ AI в UI
        const aiMessageEl = document.createElement('div');
        aiMessageEl.className = 'ai-message';
        aiMessageEl.innerHTML = `
            <div class="ai-message-bubble assistant">${escapeHtml(data.response)}</div>
        `;
        aiMessages.appendChild(aiMessageEl);
        
        // сохраняем сообщение в локальном состоянии
        aiChatState.messages.push({
            role: 'user',
            content: message
        });
        aiChatState.messages.push({
            role: 'assistant',
            content: data.response
        });
        
        // очищаем выбранное изображение
        clearAIImagePreview();
        
    } catch (error) {
        console.error('Ошибка AI чата:', error);
        
        // удаляем индикатор загрузки если он всё ещё там
        if (loadingEl && loadingEl.parentNode) {
            loadingEl.parentNode.removeChild(loadingEl);
        }
        
        // показываем понятное сообщение об ошибке
        let errorMessage = error.message;
        if (error.message.includes('llama-server') || error.message.includes('killed')) {
            errorMessage = 'AI помощник временно недоступен. Пожалуйста, попробуйте позже.';
        }
        
        const errorEl = document.createElement('div');
        errorEl.className = 'ai-message';
        errorEl.innerHTML = `
            <div class="ai-message-bubble assistant" style="background: #fecaca; border-left-color: #dc2626;">
                ❌ ${escapeHtml(errorMessage)}
            </div>
        `;
        aiMessages.appendChild(errorEl);
    } finally {
        // включаем кнопку отправки
        aiSendBtn.disabled = false;
        aiChatState.isLoading = false;
        
        // скролл вниз
        aiMessages.scrollTop = aiMessages.scrollHeight;
    }
}

function handleAIImageSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // проверяем размер файла (максимум 5МБ)
    if (file.size > 5 * 1024 * 1024) {
        alert('Файл слишком большой. Максимум 5МБ.');
        return;
    }
    
    // читаем файл как base64
    const reader = new FileReader();
    reader.onload = function(event) {
        aiChatState.selectedImage = event.target.result;
        
        // показываем превью
        const preview = document.getElementById('aiImagePreview');
        preview.src = aiChatState.selectedImage;
        preview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function clearAIImagePreview() {
    const preview = document.getElementById('aiImagePreview');
    const aiImageInput = document.getElementById('aiImageInput');
    
    aiChatState.selectedImage = null;
    preview.style.display = 'none';
    preview.src = '';
    aiImageInput.value = '';
}

function loadAIChatHistory() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!user.id) {
        // если пользователь не авторизован, пока не загружаем историю
        return;
    }
    
    // опционально: загружаем историю с сервера
    // для теперь просто используем локальное состояние
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

