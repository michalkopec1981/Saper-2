# Instalacja funkcjonalności AR (Rozszerzona Rzeczywistość)

## Problem
Zakładka AR w panelu Host wymaga biblioteki **OpenCV** do rozpoznawania obrazów. Jeśli widzisz komunikat:
```
Błąd: OpenCV nie jest zainstalowany. AR nie jest dostępne.
```

## Rozwiązanie

### Krok 1: Zainstaluj zależności
Uruchom w terminalu:

```bash
pip install -r requirements.txt
```

Lub zainstaluj tylko OpenCV:

```bash
pip install opencv-python-headless==4.8.1.78
```

**Uwaga:** Używamy `opencv-python-headless` zamiast `opencv-python` - jest to lżejsza wersja bez GUI, idealna dla serwerów.

### Krok 2: Zrestartuj aplikację
Po instalacji zrestartuj serwer Flask:

```bash
# Zatrzymaj aplikację (Ctrl+C)
# Uruchom ponownie
python app.py
```

### Krok 3: Sprawdź czy działa
Po restarcie wejdź do panelu Host → zakładka AR i spróbuj dodać nowy obiekt AR.

## Dodatkowe informacje

### Wymagania systemowe
OpenCV wymaga:
- Python 3.7+
- numpy (już zainstalowane w projekcie)

### Jeśli nadal nie działa

1. Sprawdź czy OpenCV jest zainstalowane:
```bash
python -c "import cv2; print('OpenCV version:', cv2.__version__)"
```

2. Sprawdź logi aplikacji przy starcie - powinna być informacja o OpenCV:
```
⚠️  opencv-python not installed. AR features will be limited.
```
lub
```
✅ OpenCV loaded successfully
```

### Problemy z instalacją?

Jeśli masz problemy z instalacją `opencv-python-headless`, możesz spróbować:
- Aktualizować pip: `pip install --upgrade pip`
- Zainstalować z flagą --user: `pip install --user opencv-python-headless`
- Użyć conda: `conda install -c conda-forge opencv`

## Co robi funkcjonalność AR?

1. **Host** definiuje obiekty AR - fotografuje przedmioty (np. logo, plakat)
2. **Gracze** skanują kod QR AR Scanner
3. **Gracze** fotografują te same obiekty smartfonem
4. Aplikacja rozpoznaje obiekt i uruchamia przypisaną minigrę
5. **Gracze** zdobywają punkty za rozpoznanie obiektów!

---

Jeśli wszystko działa poprawnie, funkcjonalność AR jest gotowa do użycia! 🎯📸
