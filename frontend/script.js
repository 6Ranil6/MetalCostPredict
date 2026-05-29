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
    
    // если пользователь вышел, находясь на странице личного кабинета - перезагружаем форму
    if (document.getElementById('login-form')) {
        window.location.reload();
    }
}

// проверка авторизации для доступа к калькулятору
function requireAuthorizationForCalculator() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) {
        alert('Доступ к калькулятору требует авторизации. Пожалуйста, войдите или зарегистрируйтесь.');
        window.location.href = 'auth.html';
    }
}

// инициализация при загрузке документа
document.addEventListener('DOMContentLoaded', () => {
    renderUserStatus();
    
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
    }
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
            const formData = {
                'user_id': userId, // Передается на бэкенд для привязки к predictions_history
                'Наименование': document.getElementById('name').value,
                'Категория_цены': document.getElementById('categoryPrice').value,
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
            priceDisplay.textContent = result.price.toLocaleString('ru-RU') + " руб.";
            
            // Обновляем историю после успешного расчета
            if (userId) {
                loadPredictionsHistory();
            }
        } else {
            const fileInput = document.getElementById('file-input');
            if (!fileInput || !fileInput.files[0]) {
                alert("Пожалуйста, выберите файл перед отправкой.");
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

            if (!response.ok) throw new Error('Ошибка при пакетной обработке файла');

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
        alert(error.message || "Произошла непредвиденная ошибка. Проверьте соединение с бэкендом.");
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
            
            // переадресовываем на главную
            window.location.href = "index.html";
        } else {
            const name = inputs[0].value;
            const email = inputs[1].value;
            const password = inputs[2].value;
            const confirmPassword = inputs[3].value;
            
            if (password !== confirmPassword) {
                throw new Error("Введенные пароли не совпадают!");
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
        alert(error.message);
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
        alert(error.message);
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
            throw new Error('Ошибка при загрузке истории');
        }

        const data = await response.json();
        const history = data.history || [];

        if (history.length === 0) {
            historyList.innerHTML = '<p class="history-empty">История запросов пуста</p>';
            return;
        }

        // Формируем HTML для истории
        let historyHTML = '';
        history.forEach((item, index) => {
            const date = new Date(item.created_at).toLocaleString('ru-RU');
            const productName = item.input_data['Наименование'] || 'Неизвестный продукт';
            const price = item.predicted_price.toLocaleString('ru-RU');

            historyHTML += `
                <div class="history-item">
                    <div class="history-item-info">
                        <div class="history-item-name">${productName}</div>
                        <div class="history-item-date">${date}</div>
                    </div>
                    <div class="history-item-right">
                        <div class="history-item-price">${price} ₽</div>
                        <button class="history-item-btn" onclick="showHistoryDetails(${JSON.stringify(item.input_data).replace(/"/g, '&quot;')})">Подробно</button>
                    </div>
                </div>
            `;
        });

        historyList.innerHTML = historyHTML;
    } catch (error) {
        console.error("Ошибка загрузки истории:", error);
        historyList.innerHTML = '<p class="history-empty" style="color: red;">Ошибка при загрузке истории</p>';
    }
}

// Функция для очистки отображения истории
function clearHistoryView() {
    const historyList = document.getElementById('history-list');
    if (historyList) {
        historyList.innerHTML = '<p class="history-empty">История запросов пуста</p>';
    }
}

// Функция для показа подробной информации о запросе
function showHistoryDetails(inputData) {
    let details = 'Параметры запроса:\n\n';
    for (const [key, value] of Object.entries(inputData)) {
        if (value && value !== 'отсутствует') {
            details += `${key}: ${value}\n`;
        }
    }
    alert(details);
}
