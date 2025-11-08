#!/usr/bin/env python3
"""
Skrypt do generowania domyślnych pytań AI dla wszystkich kategorii
"""

import os
import json
import sys
from anthropic import Anthropic

# Lista kategorii zgodnie z wymaganiami
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

def generate_questions_for_category(client, category_name, count=20):
    """Generuje pytania dla danej kategorii"""
    print(f"Generowanie {count} pytań dla kategorii: {category_name}...")

    prompt = f"""Wygeneruj dokładnie {count} pytań testowych z kategorii "{category_name}" na poziomie trudności: średni.

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

WAŻNE: Pytania muszą być w języku polskim i odpowiednie do poziomu trudności."""

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
        questions = json.loads(response_text)

        print(f"✓ Wygenerowano {len(questions)} pytań dla kategorii: {category_name}")
        return questions

    except Exception as e:
        print(f"✗ Błąd podczas generowania pytań dla {category_name}: {e}")
        return []

def main():
    # Sprawdź klucz API
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: Brak klucza ANTHROPIC_API_KEY w zmiennych środowiskowych")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    all_questions = {}

    for category in CATEGORIES:
        questions = generate_questions_for_category(client, category, count=20)
        if questions:
            all_questions[category] = questions

    # Zapisz do pliku JSON
    output_file = 'default_ai_questions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Wszystkie pytania zostały zapisane do pliku: {output_file}")
    print(f"Wygenerowano pytania dla {len(all_questions)} kategorii")
    total_questions = sum(len(q) for q in all_questions.values())
    print(f"Łącznie: {total_questions} pytań")

if __name__ == '__main__':
    main()
