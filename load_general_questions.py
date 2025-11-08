#!/usr/bin/env python3
"""
Skrypt do załadowania pytań ogólnych do bazy danych
Ładuje pytania z pliku default_general_questions.json
"""

import os
import sys
import json

# Dodaj ścieżkę do modułu aplikacji
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, GeneralQuestion

def load_questions_from_json(filename='default_general_questions.json'):
    """Ładuje pytania z pliku JSON do bazy danych"""

    if not os.path.exists(filename):
        print(f"ERROR: Plik {filename} nie istnieje!")
        sys.exit(1)

    with open(filename, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)

    with app.app_context():
        # Sprawdź ile pytań już istnieje
        existing_count = GeneralQuestion.query.count()
        if existing_count > 0:
            print(f"\n⚠️  W bazie istnieje już {existing_count} pytań ogólnych.")
            response = input("Czy chcesz usunąć istniejące pytania i załadować nowe? (tak/nie): ")
            if response.lower() not in ['tak', 't', 'yes', 'y']:
                print("Anulowano.")
                sys.exit(0)

            # Usuń istniejące pytania
            GeneralQuestion.query.delete()
            db.session.commit()
            print("✓ Usunięto istniejące pytania")

        total_loaded = 0

        # questions_data to dict: {category_name: {difficulty: [questions]}}
        for category_name, difficulties in questions_data.items():
            for difficulty, questions_list in difficulties.items():
                for q_data in questions_list:
                    new_question = GeneralQuestion(
                        category_name=category_name,
                        difficulty_level=difficulty,
                        text=q_data['text'],
                        option_a=q_data['option_a'],
                        option_b=q_data['option_b'],
                        option_c=q_data['option_c'],
                        correct_answer=q_data['correct_answer'].upper()
                    )
                    db.session.add(new_question)
                    total_loaded += 1

        db.session.commit()

        print(f"\n✓ Załadowano {total_loaded} pytań ogólnych do bazy danych")

        # Statystyki
        for category in questions_data.keys():
            easy_count = GeneralQuestion.query.filter_by(category_name=category, difficulty_level='easy').count()
            hard_count = GeneralQuestion.query.filter_by(category_name=category, difficulty_level='hard').count()
            print(f"  {category}: {easy_count} łatwych, {hard_count} trudnych")

if __name__ == '__main__':
    load_questions_from_json()
