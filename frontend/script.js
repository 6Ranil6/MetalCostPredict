let currentMode = 'manual'; // ручной ввод или загрузка файла

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
        fileNameDisplay.textContent = input.files[0].name;
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
            // Проверяем, что категория цены выбрана ТОЛЬКО для ручного ввода
            const categoryPrice = document.getElementById('categoryPrice').value;
            if (!categoryPrice) {
                showInfoModal('Пожалуйста, выберите категорию цены из списка', 'Внимание');
                btn.textContent = "Рассчитать стоимость";
                btn.disabled = false;
                return;
            }

            const formData = {
                'user_id': userId, // Передается на бэкенд для привязки к predictions_history
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

            response = await fetch('http://127.0.0.1:5111/predict-manual', {
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

            response = await fetch('http://127.0.0.1:5111/predict-file', {
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
            
            const response = await fetch('http://127.0.0.1:5111/api/login', {
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
            
            const response = await fetch('http://127.0.0.1:5111/api/register', {
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
        const response = await fetch('http://127.0.0.1:5111/api/feedback', {
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

// Функция для загрузки истории предсказаний пользователя
async function loadPredictionsHistory() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return;

    const historyList = document.getElementById('history-list');
    const limitInput = document.getElementById('history-limit');
    if (!historyList || !limitInput) return;

    const limit = parseInt(limitInput.value) || 50;

    try {
        const response = await fetch(`http://127.0.0.1:5111/api/predictions-history/${user.id}?limit=${limit}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        
        if (!data || !data.history) {
            throw new Error('Некорректный формат ответа от сервера');
        }
        
        let history = data.history || [];
        
        // Применяем фильтры
        history = applyHistoryFilters(history);

        if (history.length === 0) {
            historyList.innerHTML = '<p class="history-empty">История запросов пуста или не соответствует фильтрам</p>';
            return;
        }

        // Формируем HTML для истории
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

// Функция для применения фильтров к истории запросов
function applyHistoryFilters(history) {
    const searchInput = document.getElementById('history-search');
    const priceFilter = document.getElementById('history-price-filter');
    
    let filtered = history;
    
    // Фильтр по поиску в названии
    if (searchInput && searchInput.value.trim()) {
        const searchText = searchInput.value.toLowerCase().trim();
        filtered = filtered.filter(item => {
            const productName = (item.input_data && item.input_data['Наименование']) || '';
            return productName.toLowerCase().includes(searchText);
        });
    }
    
    // Фильтр по категории цены
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

// Функция для очистки отображения истории
function clearHistoryView() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return;

    // Показываем модальное окно подтверждения
    showConfirmModal(
        'Вы уверены, что хотите очистить всю историю запросов?',
        () => clearAllHistory(user.id)
    );
}

// Функция для очистки всей истории (soft delete)
async function clearAllHistory(userId) {
    try {
        const response = await fetch(`http://127.0.0.1:5111/api/hide-all-predictions/${userId}`, {
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

// Функция для удаления одного элемента истории (soft delete)
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

        // Перезагружаем историю
        loadPredictionsHistory();
    } catch (error) {
        console.error("Ошибка удаления записи:", error);
        showInfoModal(`Ошибка: ${error.message}`, "Ошибка удаления");
    }
}

// Функция для показа подробной информации о запросе в модальном окне
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

        // Открываем модальное окно
        const modal = document.getElementById('details-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    } catch (error) {
        console.error('Ошибка при отображении деталей:', error);
        showInfoModal('Ошибка при загрузке деталей запроса', "Ошибка");
    }
}

// Функция для закрытия модального окна подробной информации
function closeDetailsModal() {
    const modal = document.getElementById('details-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Функция для показа информационного модального окна (вместо alert)
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

// Переменная для сохранения callback функции подтверждения
let confirmCallback = null;

// Функция для показа модального окна подтверждения
function showConfirmModal(message, callback) {
    const confirmText = document.getElementById('confirm-text');
    if (confirmText) {
        confirmText.textContent = message;
    }
    confirmCallback = callback;

    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// Функция для закрытия модального окна подтверждения
function closeConfirmModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    confirmCallback = null;
}

// Функция для подтверждения действия
function confirmAction() {
    if (confirmCallback) {
        confirmCallback();
    }
    closeConfirmModal();
}

// Закрытие модальных окон при клике на фон
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
