let currentMode = 'manual'; // ручной ввод данных или file

function setMode(mode) {
    currentMode = mode;
    
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    if (mode === 'manual') {
        document.getElementById('manual-section').classList.remove('hidden');
        document.getElementById('file-section').classList.add('hidden');
    } else {
        document.getElementById('manual-section').classList.add('hidden');
        document.getElementById('file-section').classList.remove('hidden');
    }
    document.getElementById('result').style.display = 'none';
}

function handleFile(input) {
    if (input.files && input.files[0]) {
        document.getElementById('file-name').textContent = input.files[0].name;
    }
}

async function calculate() {
    const btn = document.querySelector('.calculate-btn');
    const resultBox = document.getElementById('result');
    const priceDisplay = document.getElementById('price-display');

    btn.textContent = "Считаем...";
    btn.disabled = true;

    try {
        let response;

        if (currentMode === 'manual') {
            const formData = {
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
                body: JSON.stringify(formData) //dump
            });
            if (!response.ok) throw new Error('Ошибка сервера');

            const result = await response.json();
                    
            priceDisplay.textContent = result.price.toLocaleString('ru-RU') + " руб.";
        } else {
            const fileInput = document.getElementById('file-input');
            const fileData = new FormData();
            fileData.append('file', fileInput.files[0]);

            response = await fetch('http://127.0.0.1:5111/predict-file', {
                method: 'POST',
                body: fileData 
            });

            if (!response.ok) throw new Error('Ошибка сервера');


            const blob = await response.blob(); // Получаем бинарные данные
            const url = window.URL.createObjectURL(blob); // Создаем URL, где лежат наши данные
            const a = document.createElement('a'); // создаем в UTL тег а
            a.href = url; // параметры прописываем
            a.download = "result_prices.csv";
            document.body.appendChild(a); // добавляем ссылку на странуцу
            a.click(); // Имитируем нажатие по ссылке
            a.remove();
            
            priceDisplay.textContent = "Файл обработан и скачан!";
        }
        
        resultBox.style.display = 'block';


    } catch (error) {
        console.error("Ошибка запроса:", error);
        alert("Произошла ошибка. Проверьте, запущен ли Python-сервер.");
    } finally {
        btn.textContent = "Рассчитать стоимость";
        btn.disabled = false;
    }
}
