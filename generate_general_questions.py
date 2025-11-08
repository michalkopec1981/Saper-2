#!/usr/bin/env python3
"""
Skrypt do generowania pytań ogólnych dla wszystkich 10 kategorii
Generuje po 10 pytań łatwych i 10 trudnych dla każdej kategorii (200 pytań total)
"""

import os
import sys
from anthropic import Anthropic

# Dodaj ścieżkę do modułu aplikacji
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, GeneralQuestion

# Lista 10 kategorii
CATEGORIES = [
    'Historia powszechna',
    'Historia Polski',
    'Geografia świata',
    'Geografia Polski',
    'Gry Komputery i sprzęt',
    'Muzyka',
    'Kuchnia',
    'Film',
    'Sport',
    'Nauki ścisłe'
]

DIFFICULTY_LEVELS = ['easy', 'hard']
DIFFICULTY_NAMES = {
    'easy': 'łatwy',
    'hard': 'trudny'
}

def generate_questions_for_category(client, category_name, difficulty, count=10):
    """Generuje pytania dla danej kategorii i poziomu trudności"""
    difficulty_pl = DIFFICULTY_NAMES[difficulty]
    print(f"Generowanie {count} pytań ({difficulty_pl}) dla kategorii: {category_name}...")

    prompt = f"""Wygeneruj dokładnie {count} pytań testowych z kategorii "{category_name}" na poziomie trudności: {difficulty_pl}.

Każde pytanie powinno:
- Mieć treść pytania (maksymalnie 200 znaków)
- Mieć 3 odpowiedzi (A, B, C) - każda maksymalnie 100 znaków
- Mieć jedną poprawną odpowiedź (A, B lub C)

Zwróć odpowiedź w formacie JSON (tylko czysty JSON, bez żadnego dodatkowego tekstu):
[
  {{
    "text": "Treść pytania?",
    "option_a": "Odpowiedź A",
    "option_b": "Odpowiedź B",
    "option_c": "Odpowiedź C",
    "correct_answer": "A"
  }},
  ...
]

WAŻNE:
- Pytania muszą być w języku polskim
- Poziom {difficulty_pl} oznacza {"podstawową wiedzę ogólną" if difficulty == 'easy' else "bardziej szczegółową i wymagającą wiedzę"}
- Pytania powinny być różnorodne i ciekawe"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Wyciągnij treść odpowiedzi
        response_text = message.content[0].text.strip()

        # Usuń ewentualne markdown backticks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Parse JSON
        import json
        questions = json.loads(response_text)

        print(f"✓ Wygenerowano {len(questions)} pytań ({difficulty_pl}) dla kategorii: {category_name}")
        return questions

    except Exception as e:
        print(f"✗ Błąd podczas generowania pytań dla {category_name} ({difficulty_pl}): {e}")
        return []

def main():
    # Sprawdź klucz API
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: Brak klucza ANTHROPIC_API_KEY w zmiennych środowiskowych")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    with app.app_context():
        # Sprawdź ile pytań już istnieje
        existing_count = GeneralQuestion.query.count()
        if existing_count > 0:
            print(f"\n⚠️  W bazie istnieje już {existing_count} pytań ogólnych.")
            response = input("Czy chcesz usunąć istniejące pytania i wygenerować nowe? (tak/nie): ")
            if response.lower() not in ['tak', 't', 'yes', 'y']:
                print("Anulowano.")
                sys.exit(0)

            # Usuń istniejące pytania
            GeneralQuestion.query.delete()
            db.session.commit()
            print("✓ Usunięto istniejące pytania")

        total_generated = 0

        for category in CATEGORIES:
            for difficulty in DIFFICULTY_LEVELS:
                questions = generate_questions_for_category(client, category, difficulty, count=10)

                if questions:
                    for q_data in questions:
                        new_question = GeneralQuestion(
                            category_name=category,
                            difficulty_level=difficulty,
                            text=q_data['text'],
                            option_a=q_data['option_a'],
                            option_b=q_data['option_b'],
                            option_c=q_data['option_c'],
                            correct_answer=q_data['correct_answer'].upper()
                        )
                        db.session.add(new_question)
                        total_generated += 1

                db.session.commit()

        print(f"\n✓ Zakończono! Wygenerowano łącznie {total_generated} pytań ogólnych")
        print(f"Kategorii: {len(CATEGORIES)}")
        print(f"Poziomy trudności: {len(DIFFICULTY_LEVELS)}")
        print(f"Oczekiwana liczba pytań: {len(CATEGORIES) * len(DIFFICULTY_LEVELS) * 10}")

if __name__ == '__main__':
    main()
