"""
CSV/JSON quiz loader for live quiz sessions.
Converts CSV/JSON files into Quiz objects.
"""

import csv
import json
import tempfile
import os
from typing import List, Dict, Optional
from models.quiz import Quiz, QuizQuestion


class CSVQuizLoader:
    """Loads quiz data from CSV/JSON files."""

    @staticmethod
    async def load_from_csv(file_path: str) -> List[Dict]:
        """
        Load quiz questions from CSV file.
        Expected format: question,option1,option2,option3,option4,correct_answer,explanation
        """
        questions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return questions
                
                for row_idx, row in enumerate(reader, start=2):
                    if len(row) < 2:
                        continue
                    
                    question = row[0].strip()
                    if not question:
                        continue
                    
                    # Get options
                    options = [opt.strip() for opt in row[1:5] if opt.strip()]
                    if len(options) < 2:
                        continue
                    
                    # Get correct answer (index or letter)
                    correct_ans = row[5].strip() if len(row) > 5 else "0"
                    try:
                        if correct_ans.isalpha() and len(correct_ans) == 1:
                            correct_idx = ord(correct_ans.upper()) - ord('A')
                        else:
                            correct_idx = int(correct_ans)
                        if not (0 <= correct_idx < len(options)):
                            correct_idx = 0
                    except (ValueError, IndexError):
                        correct_idx = 0
                    
                    # Get explanation
                    explanation = row[6].strip() if len(row) > 6 else ""
                    
                    questions.append({
                        'question': question,
                        'options': options,
                        'correct_answer': chr(ord('A') + correct_idx),
                        'correct_index': correct_idx,
                        'explanation': explanation,
                        'letter_options': [chr(ord('A') + i) for i in range(len(options))]
                    })
        except Exception as e:
            print(f"Error loading CSV: {e}")
        
        return questions

    @staticmethod
    async def load_from_json(file_path: str) -> List[Dict]:
        """
        Load quiz questions from JSON file.
        Expected format: [{"question": "", "options": [], "correct_answer": "A", "explanation": ""}]
        """
        questions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return questions
                
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    
                    question = item.get('question', '').strip()
                    if not question:
                        continue
                    
                    options = item.get('options', [])
                    if not isinstance(options, list) or len(options) < 2:
                        continue
                    
                    correct_ans = str(item.get('correct_answer', 'A')).strip().upper()
                    if len(correct_ans) == 1 and correct_ans.isalpha():
                        correct_idx = ord(correct_ans) - ord('A')
                    else:
                        try:
                            correct_idx = int(correct_ans)
                        except:
                            correct_idx = 0
                    
                    if not (0 <= correct_idx < len(options)):
                        correct_idx = 0
                    
                    explanation = item.get('explanation', '').strip()
                    
                    questions.append({
                        'question': question,
                        'options': options,
                        'correct_answer': chr(ord('A') + correct_idx),
                        'correct_index': correct_idx,
                        'explanation': explanation,
                        'letter_options': [chr(ord('A') + i) for i in range(len(options))]
                    })
        except Exception as e:
            print(f"Error loading JSON: {e}")
        
        return questions

    @staticmethod
    def create_quiz_from_questions(
        owner_id: int,
        title: str,
        questions: List[Dict],
        per_question_seconds: int = 10,
        negative_marking: float = 0.25
    ) -> Optional[Quiz]:
        """Convert loaded questions to Quiz object."""
        if not questions:
            return None
        
        quiz_questions = []
        for q_data in questions:
            try:
                qq = QuizQuestion(
                    text=q_data['question'],
                    options=q_data['options'],
                    correctIndex=q_data['correct_index'],
                    explanation=q_data.get('explanation', '')
                )
                qq.validate()
                quiz_questions.append(qq)
            except Exception as e:
                print(f"Skipping invalid question: {e}")
                continue
        
        if not quiz_questions:
            return None
        
        quiz = Quiz(
            ownerId=owner_id,
            title=title,
            description=f"CSV Quiz - {len(quiz_questions)} questions",
            shuffleQuestions=False,
            shuffleOptions=False,
            perQuestionSeconds=per_question_seconds,
            negativeMarking=negative_marking,
            questions=quiz_questions
        )
        
        try:
            quiz.validate()
            return quiz
        except Exception as e:
            print(f"Invalid quiz: {e}")
            return None


csv_quiz_loader = CSVQuizLoader()
