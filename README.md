# Saper 2 - Gra dla eventów

## Instalacja

### 1. Wymagania
- Python 3.11 lub nowszy
- PostgreSQL (dla produkcji) lub SQLite (dla developmentu)

### 2. Instalacja zależności

Aby zainstalować wszystkie wymagane pakiety, uruchom:

```bash
pip install -r requirements.txt
```

**Ważne:** Upewnij się, że instalujesz dokładnie te wersje pakietów, które są określone w `requirements.txt`. Szczególnie ważna jest zgodność wersji:
- `opencv-python==4.8.1.78`
- `numpy==1.24.3`
- `Pillow==10.1.0`

Niezgodność wersji (np. numpy 2.x zamiast 1.x) spowoduje błędy przy funkcjach AR.

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

## Rozwiązywanie problemów

### Błąd "OpenCV nie jest zainstalowane. AR nie jest dostępne"

Ten błąd pojawia się, gdy pakiety OpenCV nie są prawidłowo zainstalowane. Aby naprawić:

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

### Weryfikacja instalacji pakietów AR

Aby sprawdzić, czy wszystkie pakiety AR są prawidłowo zainstalowane:

```bash
python -c "import cv2; import numpy as np; from PIL import Image; print('✓ Wszystkie pakiety AR działają poprawnie')"
```

Jeśli widzisz komunikat "✓ Wszystkie pakiety AR działają poprawnie", oznacza to, że instalacja przebiegła pomyślnie.
