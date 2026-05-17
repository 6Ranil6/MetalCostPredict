## Запуск с красивым отчётом
```bash
# Просто запуск
pytest tests/test_base.py
pytest tests/test_advanced.py
```

```bash
# HTML отчёт о покрытии (откроется в браузере)
pytest tests/test_base.py --cov=preProcessor --cov=parser_23MET \
    --cov-report=html --cov-report=term-missing
pytest tests/test_advanced.py --cov=preProcessor --cov=parser_23MET \
    --cov-report=html --cov-report=term-missing
```
