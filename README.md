# Saper 2 - Gra dla eventów

## Instalacja

### 1. Wymagania
- Python 3.10 lub nowszy (runtime.txt określa wersję dla deploymentu)
- PostgreSQL (dla produkcji) lub SQLite (dla developmentu)

### 2. Instalacja zależności

Aby zainstalować wszystkie wymagane pakiety, uruchom:

```bash
pip install -r requirements.txt
```

**Ważne:** Upewnij się, że instalujesz dokładnie te wersje pakietów, które są określone w `requirements.txt`. Szczególnie ważna jest zgodność wersji:
- `opencv-python-headless==4.8.1.78` (wersja headless dla środowisk serwerowych)
- `numpy==1.24.3`
- `Pillow==10.1.0`

Niezgodność wersji (np. numpy 2.x zamiast 1.x) spowoduje błędy przy funkcjach AR.

**Dla środowisk kontenerowych (Heroku, Render, Railway, etc.):**
- Plik `Aptfile` zawiera systemowe zależności wymagane przez OpenCV
- Używana jest wersja `opencv-python-headless` zamiast `opencv-python` (bez GUI, lepsza dla serwerów)

### 3. Konfiguracja

Utwórz plik `.env` w katalogu głównym projektu i skonfiguruj zmienne środowiskowe:

```
SECRET_KEY=twoj-tajny-klucz
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### 4. Uruchomienie

```bash
python app.py
```

## Deployment (Heroku, Render, Railway, etc.)

Aplikacja jest skonfigurowana do automatycznego deploymentu na platformach kompatybilnych z Heroku:

### Wymagane pliki:
- `Procfile` - konfiguracja serwera (gunicorn z gevent)
- `runtime.txt` - wersja Pythona (3.10.11)
- `requirements.txt` - zależności Python
- `Aptfile` - systemowe biblioteki dla OpenCV (libgl1-mesa-glx, libglib2.0-0, etc.)

### Po wdrożeniu:
1. Aplikacja automatycznie zainstaluje pakiety z `requirements.txt`
2. Systemowe biblioteki z `Aptfile` zostaną zainstalowane (jeśli platforma to wspiera)
3. Sprawdź logi czy nie ma błędu `⚠️ opencv-python not installed`
4. Jeśli błąd występuje, sprawdź czy platforma wspiera buildpack `heroku/python` i apt buildpack

## Rozwiązywanie problemów

### Błąd "OpenCV nie jest zainstalowane. AR nie jest dostępne"

Ten błąd pojawia się, gdy pakiety OpenCV nie są prawidłowo zainstalowane.

#### Dla lokalnego developmentu:

1. Upewnij się, że masz zainstalowane wszystkie pakiety:
```bash
pip install -r requirements.txt
```

2. Sprawdź wersję numpy (musi być 1.24.3):
```bash
python -c "import numpy; print(numpy.__version__)"
```

3. Jeśli numpy jest w wersji 2.x, zainstaluj ponownie właściwą wersję:
```bash
pip install numpy==1.24.3
```

4. Zrestartuj aplikację po zainstalowaniu pakietów.

#### Dla środowiska kontenerowego/produkcyjnego:

1. **Sprawdź logi kontenera** - poszukaj linii `⚠️ opencv-python not installed`

2. **Upewnij się, że platforma wspiera Aptfile:**
   - Heroku: Dodaj buildpack `heroku-community/apt`
   - Render: Aptfile jest wspierane natywnie
   - Railway: Może wymagać Dockerfile z instalacją apt packages

3. **Pliki wymagane dla OpenCV w kontenerze:**
   - `Aptfile` - zawiera systemowe zależności (libgl1-mesa-glx, etc.)
   - `requirements.txt` - musi zawierać `opencv-python-headless` (nie `opencv-python`)

4. **Redeploy aplikacji** po dodaniu/zmianie plików Aptfile lub requirements.txt

### Weryfikacja instalacji pakietów AR

Aby sprawdzić, czy wszystkie pakiety AR są prawidłowo zainstalowane:

```bash
python -c "import cv2; import numpy as np; from PIL import Image; print('✓ Wszystkie pakiety AR działają poprawnie')"
```

Jeśli widzisz komunikat "✓ Wszystkie pakiety AR działają poprawnie", oznacza to, że instalacja przebiegła pomyślnie.
