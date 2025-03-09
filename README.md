# 1. Установка

### 0. Установите git и git lfs

### 1.Скачайте репозиторий
```commandline
git lfs install
git clone https://github.com/Xalerablt/kinoteka
cd kinoteka
git clone https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe ./nomic-ai/nomic-embed-text-v2-moe
git clone https://huggingface.co/nomic-ai/nomic-bert-2048 ./nomic-ai/nomic-bert-2048
```
### 2. Создайте виртуальное окружение (venv)
```commandline
python -m venv venv
```
### 3. Установка зависимостей
**Linux**:
```commandline
source venv/bin/activate
pip install -r requirements.txt
```
**Windows**:
```commandline
venv\Scripts\activate.bat
pip install -r requirements.txt
```
### 4. Запуск

```commandline
python app.py
```

