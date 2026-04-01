"""Utility functions for CSV and JSON import/export of quiz data"""
import csv
import json
import io
import re
import os
from typing import List, Dict, Any, Optional


CSV_EXPORT_FIELDS = [
    'questions',
    'option1',
    'option2',
    'option3',
    'option4',
    'option5',
    'answer',
    'explanation',
    'type',
    'section',
]


def _sanitize_explanation_for_csv(explanation: str) -> str:
    """Remove links and the configured QUIZ_EXPLANATION_LINK (label + URL) fully.

    - Strips any http(s) URLs
    - Strips telegram short links (t.me/...)
    - Removes the exact value of QUIZ_EXPLANATION_LINK if present
    - If QUIZ_EXPLANATION_LINK contains a URL, removes any bracketed block that
      contains that URL (e.g., "[Label: t.me/xxx]") and leftover label text
    """
    text = str(explanation or "")

    qel = os.getenv('QUIZ_EXPLANATION_LINK', '') or ''
    # Support legacy misspelled env variable
    if not qel:
        qel = os.getenv('QUIZ_EXPLAINATION_LINK', '') or ''
    qel = qel.strip()

    # Remove exact configured explanation link if present
    if qel:
        text = text.replace(qel, '')

    # Detect URL inside the configured QEL (http(s) or t.me)
    url_match = None
    if qel:
        url_match = re.search(r"(https?://\S+|t\.me/\S+)", qel)

    # Remove raw URLs from text
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"t\.me/\S+", "", text)

    # If QEL had a URL, remove any bracketed block that contains that URL
    if url_match:
        url = re.escape(url_match.group(1))
        text = re.sub(r"\[[^\]]*" + url + r"[^\]]*\]", "", text)
        # Also remove any leftover label (prefix before URL in QEL)
        label = qel.split(url_match.group(1))[0].strip().rstrip(':|-')
        if label:
            # Remove occurrences of the label with optional trailing punctuation/spaces
            text = re.sub(r"\b" + re.escape(label) + r"\b\s*[:\-–—| ]*", "", text)

    # Collapse extra whitespace
    return re.sub(r"\s+", " ", text).strip()


def quiz_to_csv(quiz_data: List[Dict[str, Any]]) -> str:
    """
    Convert quiz data to CSV string using the requested schema:
    columns: question, option1, option2, option3, option4, option5, answer, explination

    Notes:
    - "answer" is 1-based index (1..5) of the correct option
    - "option5" is optional; left empty when only four options exist
    - We intentionally keep the misspelling "explination" to match the user's format
    - QUIZ_MARKER is removed from exported question text
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(CSV_EXPORT_FIELDS)
    
    for quiz in quiz_data:
        normalized = normalize_quiz_for_csv(quiz)
        writer.writerow([normalized[field] for field in CSV_EXPORT_FIELDS])
    
    return output.getvalue()


def normalize_quiz_for_csv(quiz: Dict[str, Any]) -> Dict[str, str]:
    """Normalize quiz or poll dictionary to the CSV schema."""
    record = {field: '' for field in CSV_EXPORT_FIELDS}
    if not quiz:
        # Set default values for type and section
        record['type'] = '1'
        record['section'] = '1'
        return record

    marker_sources = [
        quiz.get('_quiz_marker'),
        quiz.get('quiz_marker'),
        os.getenv('QUIZ_MARKER')
    ]
    marker = ''
    for candidate in marker_sources:
        if candidate:
            marker = str(candidate).strip()
            if marker:
                break

    def strip_marker(text: str) -> str:
        if not text:
            return ''
        text = str(text).strip()
        if marker and text.startswith(marker):
            text = text[len(marker):].lstrip()
        elif text.startswith('['):
            text = re.sub(r'^\[[^\]]+\]\s*', '', text, count=1).strip()
        return text

    question = (
        quiz.get('questions')
        or quiz.get('question_description')
        or quiz.get('question')
        or ''
    )
    record['questions'] = strip_marker(question)

    # Populate options from option1..option5 if present
    options = []
    if any(quiz.get(f'option{i}') for i in range(1, 6)):
        for idx in range(1, 6):
            value = quiz.get(f'option{idx}')
            options.append(str(value) if value is not None else '')
    else:
        raw_options = quiz.get('options') or []
        if isinstance(raw_options, dict):
            ordered = [raw_options.get(letter) for letter in ['A', 'B', 'C', 'D', 'E']]
        else:
            ordered = list(raw_options) if isinstance(raw_options, list) else []
        options = [str(opt) if opt is not None else '' for opt in ordered]

    while len(options) < 5:
        options.append('')
    options = options[:5]

    for idx, value in enumerate(options, start=1):
        record[f'option{idx}'] = value

    answer_raw = quiz.get('answer')
    answer_index = None
    if isinstance(answer_raw, str):
        stripped = answer_raw.strip()
        if ':' in stripped:
            idx_part = stripped.split(':', 1)[0].strip()
            if idx_part.lstrip('-').isdigit():
                answer_index = int(idx_part)
        elif stripped.lstrip('-').isdigit():
            num = int(stripped)
            if num <= 0:
                answer_index = 0
            else:
                # Legacy values were 1-based
                answer_index = num - 1
        else:
            letter_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
            answer_index = letter_map.get(stripped.upper())
    elif isinstance(answer_raw, int):
        answer_index = answer_raw

    if answer_index is None and isinstance(quiz.get('correct_answer_index'), int):
        answer_index = quiz['correct_answer_index']
    if answer_index is None and quiz.get('correct_option'):
        letter_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
        answer_index = letter_map.get(str(quiz['correct_option']).upper())
    if answer_index is None:
        answer_index = 0

    if answer_index < 0:
        answer_index = 0
    if answer_index >= len(options):
        answer_index = 0

    record['answer'] = str(answer_index + 1)

    record['explanation'] = _sanitize_explanation_for_csv(quiz.get('explanation', ''))
    
    # Set type and section (default to '1' if not provided)
    record['type'] = str(quiz.get('type', '1'))
    record['section'] = str(quiz.get('section', '1'))
    
    return record


def csv_to_quiz(csv_string: str) -> List[Dict[str, Any]]:
    """
    Convert CSV string to internal quiz data format.

    Supported schemas (auto-detected by header names):
    1) Requested schema: question, option1..option5, answer (1-based), explination
    2) Legacy schema: Question, Option A..Option D, Correct Answer (Letter/Index), Explanation
    """
    quiz_data = []
    
    try:
        reader = csv.DictReader(io.StringIO(csv_string))
        
        for row in reader:
            # Detect question field
            question = (row.get('questions') or row.get('question') or row.get('Question') or '').strip()
            if not question:
                continue
            
            # Prefer new schema option keys, fall back to legacy
            options_new = [
                (row.get('option1') or '').strip(),
                (row.get('option2') or '').strip(),
                (row.get('option3') or '').strip(),
                (row.get('option4') or '').strip(),
                (row.get('option5') or '').strip(),
            ]
            if any(options_new[:4]):
                options = options_new
            else:
                options = [
                    (row.get('Option A') or '').strip(),
                    (row.get('Option B') or '').strip(),
                    (row.get('Option C') or '').strip(),
                    (row.get('Option D') or '').strip(),
                ]
            
            # Filter out empty options (in case CSV has fewer than 4)
            options = [opt for opt in options if opt]
            
            # Ensure we have at least 4 options (support 5th if available)
            while len(options) < 4:
                options.append('')
            options = options[:5]
            
            # Get correct answer from either schema
            # New schema: 1-based index in 'answer'
            answer_field = (row.get('answer') or '').strip()
            correct_answer_index: Optional[int] = None
            if answer_field:
                parsed = answer_field.strip()
                option_match = re.match(r"option(\d+)\s*:\s*(\d+)", parsed, re.IGNORECASE)
                if option_match:
                    try:
                        correct_answer_index = int(option_match.group(2)) - 1
                    except ValueError:
                        correct_answer_index = None
                else:
                    if ':' in parsed:
                        parsed_prefix = parsed.split(':', 1)[0].strip()
                    else:
                        parsed_prefix = parsed
                    if parsed_prefix.lstrip('-').isdigit():
                        try:
                            numeric_val = int(parsed_prefix)
                            if numeric_val <= 0:
                                correct_answer_index = 0
                            else:
                                correct_answer_index = max(1, min(numeric_val, len(options))) - 1
                        except (TypeError, ValueError):
                            correct_answer_index = None
                    elif parsed.strip().upper()[:1] in {'A', 'B', 'C', 'D', 'E'}:
                        letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
                        correct_answer_index = letter_to_index.get(parsed.strip().upper()[:1], 0)
                    else:
                        correct_answer_index = None

            # Legacy fallbacks
            if correct_answer_index is None:
                correct_option_letter = (row.get('Correct Answer (Letter)') or '').strip().upper()
                correct_index_legacy = (row.get('Correct Answer (Index)') or '').strip()
                try:
                    correct_answer_index = int(correct_index_legacy) if correct_index_legacy else None
                except (TypeError, ValueError):
                    correct_answer_index = None
                if correct_answer_index is None and correct_option_letter:
                    letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                    correct_answer_index = letter_to_index.get(correct_option_letter, 0)

            # Final clamp and defaults
            if correct_answer_index is None:
                correct_answer_index = 0
            if correct_answer_index < 0 or correct_answer_index >= len(options):
                correct_answer_index = 0
            
            # Get explanation
            explanation = (row.get('explination') or row.get('Explanation') or '').strip()
            
            quiz_data.append({
                'question_description': question,
                'options': options[:4] if len(options) < 5 else options[:5],
                'correct_answer_index': correct_answer_index,
                'correct_option': '',  # not needed for CSV import; computed elsewhere if needed
                'explanation': explanation,
                'type': row.get('type', '1'),
                'section': row.get('section', '1')
            })
    
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")
    
    return quiz_data


def quiz_to_json(quiz_data: List[Dict[str, Any]]) -> str:
    """
    Convert quiz data to JSON format.
    
    Args:
        quiz_data: List of quiz dictionaries
    
    Returns:
        JSON string (pretty-printed)
    """
    # Remove QUIZ_MARKER from question descriptions before exporting
    import os
    QUIZ_MARKER = os.getenv('QUIZ_MARKER', '')
    
    cleaned_data = []
    for quiz in quiz_data:
        cleaned_quiz = quiz.copy()
        question = quiz.get('question_description', '')
        if QUIZ_MARKER and question.startswith(QUIZ_MARKER):
            # Remove QUIZ_MARKER and any following newlines/whitespace
            cleaned_quiz['question_description'] = question[len(QUIZ_MARKER):].lstrip('\n').strip()
        cleaned_data.append(cleaned_quiz)
    
    return json.dumps(cleaned_data, ensure_ascii=False, indent=2)


def json_to_quiz(json_string: str) -> List[Dict[str, Any]]:
    """
    Convert JSON string to quiz data format.
    
    Args:
        json_string: JSON string containing array of quiz objects
    
    Returns:
        List of quiz dictionaries
    """
    try:
        data = json.loads(json_string)
        
        # Ensure it's a list
        if not isinstance(data, list):
            raise ValueError("JSON must contain an array of quiz objects")
        
        # Validate each quiz object
        quiz_data = []
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # Ensure required fields
            question = item.get('question_description', '').strip()
            if not question:
                continue
            
            options = item.get('options', [])
            if not isinstance(options, list):
                continue
            
            # Ensure we have 4 options
            while len(options) < 4:
                options.append('')
            options = options[:4]
            
            # Get correct answer
            correct_answer_index = item.get('correct_answer_index')
            correct_option = item.get('correct_option', '')
            
            # Validate and convert
            if correct_answer_index is None:
                # Try to get from correct_option
                if correct_option:
                    letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                    correct_answer_index = letter_to_index.get(correct_option.upper(), 0)
                else:
                    correct_answer_index = 0
            
            if not correct_option and correct_answer_index is not None:
                index_to_letter = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
                correct_option = index_to_letter.get(correct_answer_index, 'A')
            
            # Ensure index is valid
            if correct_answer_index < 0 or correct_answer_index >= 4:
                correct_answer_index = 0
                correct_option = 'A'
            
            quiz_data.append({
                'question_description': question,
                'options': options,
                'correct_answer_index': correct_answer_index,
                'correct_option': correct_option,
                'explanation': item.get('explanation', '')
            })
        
        return quiz_data
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error parsing JSON: {str(e)}")

