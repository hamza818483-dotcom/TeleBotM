"""PDF exporter service for generating quiz PDFs from quiz data"""
import os
import re
from typing import List, Dict, Any
from jinja2 import Template


class PDFExporter:
    """Handles PDF generation from quiz data using HTML templates"""
    
    def __init__(self):
        # Match converter.py format: [a], [b], [c], [d]
        self.bengali_font = 'SolaimanLipi'
        self.long_option_threshold = 16  # Match converter.py
        self.answer_circles = {
            'A': '[a]', 'B': '[b]', 'C': '[c]', 'D': '[d]'
        }
    
    def get_exam_name_from_filename(self, filename: str) -> str:
        """Extract exam name from filename - matching converter.py"""
        if not filename:
            return "Practice Test"
        from pathlib import Path
        exam_name = Path(filename).stem
        exam_name = exam_name.replace('_', ' ')
        return exam_name
    
    def check_short_option(self, options: Dict[str, str]) -> bool:
        """Check if options are short (17 chars or less) - matching converter.py"""
        import re
        clean_lengths = []
        for option in options.values():
            if option:
                # Remove HTML tags for length calculation
                clean_text = re.sub(r'<[^>]+>', '', option).strip()
                clean_lengths.append(len(clean_text))
        return all(length <= self.long_option_threshold for length in clean_lengths if length > 0)
    
    def normalize_json_format(self, json_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert JSON formats to unified format - matching converter.py"""
        if not json_data:
            return []
        
        unified_questions = []
        for item in json_data:
            if isinstance(item, dict):
                # Standard dict format
                question = item.get('question_description', '') or item.get('question', '')
                if not question:
                    continue
                
                # Get options
                options_list = item.get('options', [])
                if not isinstance(options_list, list) or len(options_list) < 4:
                    continue
                
                # Map to A/B/C/D format
                options_dict = {
                    'A': options_list[0] if len(options_list) > 0 else '',
                    'B': options_list[1] if len(options_list) > 1 else '',
                    'C': options_list[2] if len(options_list) > 2 else '',
                    'D': options_list[3] if len(options_list) > 3 else '',
                }
                
                # Get correct answer
                correct_index = item.get('correct_answer_index', 0)
                try:
                    correct_index = int(correct_index)
                except (TypeError, ValueError):
                    correct_index = 0
                
                # Map index to letter
                index_to_letter = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
                correct_answer = index_to_letter.get(correct_index, 'A')
                
                # Get explanation
                explanation = item.get('explanation', '')
                
                unified_questions.append({
                    'question': question,
                    'options': options_dict,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })
            elif isinstance(item, list) and len(item) >= 3:
                # List format: [question, options_text, correct_answer, explanation]
                question_text = item[0] if len(item) > 0 else ""
                options_text = item[1] if len(item) > 1 else ""
                correct_answer = item[2] if len(item) > 2 else ""
                explanation = item[3] if len(item) > 3 else ""
                
                # Parse options from pipe-separated string
                option_parts = options_text.split("|") if options_text else []
                options_dict = {}
                option_keys = ["A", "B", "C", "D"]
                for i, option_key in enumerate(option_keys):
                    if i < len(option_parts):
                        options_dict[option_key] = option_parts[i].strip()
                    else:
                        options_dict[option_key] = ""
                
                unified_questions.append({
                    'question': question_text,
                    'options': options_dict,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })
        
        return unified_questions
    
    def prepare_questions(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare questions with format detection - matching converter.py"""
        prepared_questions = []
        for q in questions_data:
            question_text = q.get('question', '')
            options = {opt: q.get('options', {}).get(opt, '') for opt in ['A', 'B', 'C', 'D']}
            explanation = q.get('explanation', '')
            correct_answer = q.get('correct_answer', '').strip().upper()
            is_short_option = self.check_short_option(options)
            answer_circle = self.answer_circles.get(correct_answer, correct_answer)
            prepared_questions.append({
                'question': question_text,
                'options': options,
                'explanation': explanation,
                'correct_answer': correct_answer,
                'answer_circle': answer_circle,
                'is_short_option': is_short_option
            })
        return prepared_questions
    
    def create_format1_html(self, questions: List[Dict[str, Any]], exam_name: str) -> str:
        """Create Format 1 HTML - Practice Sheet with answers and explanations"""
        
        template_str = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ exam_name }} - Practice Sheet</title>

    <!-- MathJax Configuration -->
    <script>
        MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: { renderActions: { addMenu: [0, '', ''] } },
            startup: {
                ready() {
                    MathJax.startup.defaultReady();
                    console.log('MathJax ready for Format 1');
                }
            }
        };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <!-- Import Poppins font -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@200&display=swap" rel="stylesheet" />
    
    <!-- Bengali Font Support - Noto Sans Bengali -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        @page {
            size: A4 portrait;
            margin: 10mm 10mm;
        }

        body {
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.2;
            color: #000000;
            margin: 0;
            padding: 10px;
            width: 210mm;
            max-width: 210mm;
        }

        .exam-header {
            text-align: center;
            border: 2px solid #4169E1;
            background-color: #F0F8FF;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 15px;
        }

        .exam-header h1 {
            color: #191970;
            margin: 0;
            font-size: 15pt;
            font-weight: bold;
        }

        .content-columns {
            column-count: 2;
            column-gap: 15px;
            column-fill: balance;
            column-rule: 1px solid #ddd;
        }

        .question {
            margin-bottom: 7px;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .question-header {
            margin-bottom: 4px;
            display: flex;
            align-items: flex-start;
        }

        .question-num {
            font-family: 'Times New Roman', serif;
            font-weight: bold;
            color: #1E64B7;
            font-size: 12pt;
            margin-right: 5px;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .question-text {
            flex: 1;
            line-height: 1.4;
            font-size: 13pt;
            color: #000000;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }

        /* Short options table - 2 columns x 2 rows with answer in 3rd col 2nd row */
        .options-table-short {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0 4px 8px;
            table-layout: fixed;
        }

        .options-table-short td {
            border: none;
            padding: 2px 8px 2px 0;
            vertical-align: top;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 13pt;
            color: #000000;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }

        .option-col {
            width: 40%;
        }

        .options-table-short td.answer-col {
            display: flex;
            justify-content: center;
            align-items: center;
            vertical-align: middle;
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 12pt;
            color: #000000;
            padding-left: 10px;
        }
        .answer-circle {
            font-weight: 300;
            font-family: 'Poppins', sans-serif;
            font-size: 12pt;
            line-height: 1;
        }

        /* Long options - list */
        .options-list {
            margin: 4px 0 4px 8px;
            padding: 0;
            list-style: none;
        }

        .options-list li {
            margin: 1px 0;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 13pt;
            color: #000000;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }

        .option-with-answer {
            display: flex;
            font-family: 'Poppins', sans-serif;
            justify-content: space-between;
            align-items: flex-start;
        }

        .explanation {
            margin: 4px 0 2px 8px;
            padding: 4px;
            color: #000000;
            background-color: rgba(66, 153, 225, 0.1);
            border-left: 3px solid #4299e1;
            font-size: 12pt;
            font-style: italic;
            break-inside: avoid;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }

        .explanation-label {
            font-weight: bold;
            color: #2c5282;
        }

        /* MathJax styling */
        mjx-container {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
            display: inline-block;
            margin: 0 1px;
            color: #000000;
        }

        mjx-container[jax="CHTML"] {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }

        .MathJax_Display {
            text-align: left !important;
            margin: 0.2em 0 !important;
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
        }

        img {
            max-width: 35% !important;
            height: auto !important;
            vertical-align: middle;
        }

        math {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }

        @media print {
            @page {
                size: A4 portrait;
                margin: 10mm 10mm;
            }

            body {
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
                width: 210mm;
                max-width: 210mm;
            }

            .question {
                break-inside: avoid;
                page-break-inside: avoid;
            }

            .explanation {
                break-inside: avoid;
                page-break-inside: avoid;
            }

            .content-columns {
                column-rule: 1px solid #ddd;
            }
        }
    </style>
</head>
<body>
    <div class="exam-header">
        <h1>{{ exam_name }} - Practice Sheet</h1>
    </div>

    <div class="content-columns">
        {% for question in questions %}
        <div class="question">
            <div class="question-header">
                <span class="question-num">{{ "{:02d}".format(loop.index) }}.</span>
                <div class="question-text">{{ question.question|safe }}</div>
            </div>

            {% if question.is_short_option %}
            <!-- Short options - 2x2 table with answer in 3rd column, 2nd row -->
            <table class="options-table-short">
                <tr>
                    <td class="option-col">(A) {{ question.options.A|safe }}</td>
                    <td class="option-col">(B) {{ question.options.B|safe }}</td>
                    <td rowspan="2" class="answer-col">
                        <span class="answer-circle">{{ question.answer_circle }}</span>
                    </td>
                </tr>
                <tr>
                    <td class="option-col">(C) {{ question.options.C|safe }}</td>
                    <td class="option-col">(D) {{ question.options.D|safe }}</td>
                </tr>
            </table>
            {% else %}
            <!-- Long options - list with answer after 4th option -->
            <ul class="options-list">
                <li>(A) {{ question.options.A|safe }}</li>
                <li>(B) {{ question.options.B|safe }}</li>
                <li>(C) {{ question.options.C|safe }}</li>
                <li class="option-with-answer">
                    <span>(D) {{ question.options.D|safe }}</span>
                    <span class="answer-circle">{{ question.answer_circle }}</span>
                </li>
            </ul>
            {% endif %}

            {% if question.explanation %}
            <div class="explanation">
                <span class="explanation-label">ব্যাখ্যা:</span> {{ question.explanation|safe }}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <script>
        window.addEventListener('load', function () {
            if (typeof MathJax !== 'undefined') {
                MathJax.startup.promise.then(() => {
                    document.body.setAttribute('data-ready', 'true');
                    console.log('Format 1 ready for PDF generation');
                });
            } else {
                document.body.setAttribute('data-ready', 'true');
            }
        });
    </script>
</body>
</html>
'''
        
        template = Template(template_str)
        return template.render(questions=questions, exam_name=exam_name)
    
    def create_format2_html(self, questions: List[Dict[str, Any]], exam_name: str) -> str:
        """Create Format 2 HTML - Questions only in 2 columns, then answers table"""
        
        template_str = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ exam_name }} - Question Answer Sheet</title>
   
    <!-- MathJax Configuration -->
    <script>
        MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: {
                renderActions: {
                    addMenu: [0, '', '']
                }
            },
            startup: {
                ready() {
                    MathJax.startup.defaultReady();
                    console.log('MathJax ready for Format 2');
                }
            }
        };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <!-- Bengali Font Support - Noto Sans Bengali -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap" rel="stylesheet">
   
    <style>
        @page {
            size: A4 portrait;
            margin: 10mm 10mm;
        }
       
        body {
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.2;
            color: #333;
            margin: 0;
            padding: 10px;
            width: 210mm;
            max-width: 210mm;
        }
       
        .exam-header {
            text-align: center;
            border: 2px solid #4169E1;
            background-color: #F0F8FF;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 15px;
        }
       
        .exam-header h1 {
            color: #191970;
            margin: 0;
            font-size: 15pt;
            font-weight: bold;
        }
       
        .questions-section {
            column-count: 2;
            column-gap: 15px;
            column-fill: balance;
            column-rule: 1px solid #ddd;
        }
       
        .question {
            margin-bottom: 8px;
            break-inside: avoid;
            page-break-inside: avoid;
        }
       
        .question-header {
            margin-bottom: 4px;
            display: flex;
            align-items: flex-start;
        }
       
        .question-num {
            font-family: 'Times New Roman', serif;
            font-weight: bold;
            color: #1E64B7;
            font-size: 12pt;
            margin-right: 5px;
            white-space: nowrap;
            flex-shrink: 0;
        }
       
        .question-text {
            flex: 1;
            line-height: 1.4;
            font-size: 13pt;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        /* Short options - 2x2 invisible table */
        .options-table-short {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0 4px 8px;
            border: none !important;
        }
       
        .options-table-short td {
            border: none !important;
            padding: 1px 4px 1px 0;
            vertical-align: top;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 12pt;
            width: 50%;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        .options-table-short tr {
            border: none !important;
        }
       
        /* Long options - simple list */
        .options-list {
            margin: 4px 0 4px 8px;
            padding: 0;
            list-style: none;
        }
       
        .options-list li {
            margin: 1px 0;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 12pt;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        .page-break {
            page-break-before: always;
            break-before: page;
        }
       
        .answers-section {
            column-count: 1;
            margin-top: 0;
        }
       
        /* Remove all page break properties from the answer table */
        .answer-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 0;
            border: 1px solid #333;
            page-break-inside: auto !important;
            break-inside: auto !important;
        }
       
        .answer-table th, .answer-table td {
            border: 1px solid #333 !important;
            padding: 6px;
            text-align: left;
            vertical-align: top;
            page-break-inside: auto !important;
            break-inside: auto !important;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        .answer-table th {
            background-color: #f5f5f5;
            font-weight: bold;
            text-align: center;
            font-size: 13pt;
        }
       
        .answer-table tr {
            border: 1px solid #333 !important;
            page-break-inside: auto !important;
            break-inside: auto !important;
        }
       
        .qno-col { width: 8%; text-align: center; }
        .ans-col { width: 8%; text-align: center; font-weight: bold; font-size: 14pt; }
        .exp-col { width: 84%; font-size: 12pt; }
       
        .answer-table .qno-col, .answer-table .ans-col {
            text-align: center;
        }
       
        .explanation-container {
            margin: 0;
            padding: 0;
        }
       
        .explanation-header {
            margin-bottom: 2px !important;
        }
       
        .answers-section {
            page-break-inside: auto !important;
            break-inside: auto !important;
        }
       
        @media print {
            @page {
                size: A4 portrait;
                margin: 10mm 10mm;
            }
           
            body {
                width: 210mm;
                max-width: 210mm;
            }
           
            .answer-table, .answer-table th, .answer-table td, .answer-table tr {
                border: 1px solid #333 !important;
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
           
            .answer-table tbody tr {
                page-break-inside: auto !important;
                break-inside: auto !important;
            }
           
            .answer-table thead {
                display: table-header-group;
            }
           
            .options-table-short, .options-table-short td, .options-table-short tr {
                border: none !important;
            }
           
            .answers-section {
                margin-top: 0 !important;
                padding-top: 0 !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }
           
            .explanation-header {
                margin-bottom: 1px !important;
            }
           
            .answer-table {
                margin-top: 0 !important;
                border-spacing: 0;
                page-break-before: auto !important;
                break-before: auto !important;
            }
           
            .explanation-container + .answers-section,
            .explanation-header + .answers-section {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
        }
       
        /* MathJax styling with Calibri Math font */
        mjx-container {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
            display: inline-block;
            margin: 0 1px;
        }
       
        mjx-container[jax="CHTML"] {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }
       
        .MathJax_Display {
            text-align: left !important;
            margin: 0.2em 0 !important;
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
        }
       
        img {
            max-width: 35% !important;
            height: auto !important;
            vertical-align: middle;
        }
       
        math {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }
    </style>
</head>
<body>
    <div class="exam-header">
        <h1>{{ exam_name }} - Questions</h1>
    </div>
   
    <div class="questions-section">
        {% for question in questions %}
        <div class="question">
            <div class="question-header">
                <span class="question-num">{{ "{:02d}".format(loop.index) }}.</span>
                <div class="question-text">{{ question.question|safe }}</div>
            </div>
           
            {% if question.is_short_option %}
            <!-- Short options - 2x2 invisible table -->
            <table class="options-table-short">
                <tr>
                    <td>(A) {{ question.options.A|safe }}</td>
                    <td>(B) {{ question.options.B|safe }}</td>
                </tr>
                <tr>
                    <td>(C) {{ question.options.C|safe }}</td>
                    <td>(D) {{ question.options.D|safe }}</td>
                </tr>
            </table>
            {% else %}
            <!-- Long options - simple list -->
            <ul class="options-list">
                <li>(A) {{ question.options.A|safe }}</li>
                <li>(B) {{ question.options.B|safe }}</li>
                <li>(C) {{ question.options.C|safe }}</li>
                <li>(D) {{ question.options.D|safe }}</li>
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
   
    <div class="page-break"></div>
   
    <div class="answers-section">
        <table class="answer-table">
            <thead>
                <tr>
                    <th class="qno-col">Q.No.</th>
                    <th class="ans-col">Ans</th>
                    <th class="exp-col">Explanation</th>
                </tr>
            </thead>
            <tbody>
                {% for question in questions %}
                <tr>
                    <td class="qno-col">{{ loop.index }}</td>
                    <td class="ans-col">{{ question.correct_answer }}</td>
                    <td class="exp-col">
                        {% if question.explanation %}{{ question.explanation|safe }}{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
   
    <script>
        window.addEventListener('load', function() {
            if (typeof MathJax !== 'undefined') {
                MathJax.startup.promise.then(() => {
                    document.body.setAttribute('data-ready', 'true');
                    console.log('Format 2 ready for PDF generation');
                });
            } else {
                document.body.setAttribute('data-ready', 'true');
            }
        });
    </script>
</body>
</html>
'''
        template = Template(template_str)
        return template.render(questions=questions, exam_name=exam_name)
    
    def create_format3_html(self, questions: List[Dict[str, Any]], exam_name: str) -> str:
        """Create Format 3 HTML - Exam Style: Questions in 2 columns, Answer key at bottom (no explanations)"""
        
        template_str = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ exam_name }} - Exam Sheet</title>
   
    <!-- MathJax Configuration -->
    <script>
        MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: {
                renderActions: {
                    addMenu: [0, '', '']
                }
            },
            startup: {
                ready() {
                    MathJax.startup.defaultReady();
                    console.log('MathJax ready for Format 3');
                }
            }
        };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <!-- Bengali Font Support - Noto Sans Bengali -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap" rel="stylesheet">
   
    <style>
        @page {
            size: A4 portrait;
            margin: 10mm 10mm;
        }
       
        body {
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.3;
            color: #000000;
            margin: 0;
            padding: 10px;
            width: 210mm;
            max-width: 210mm;
        }
       
        .exam-header {
            text-align: center;
            border: 2px solid #4169E1;
            background-color: #F0F8FF;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 15px;
        }
       
        .exam-header h1 {
            color: #191970;
            margin: 0;
            font-size: 15pt;
            font-weight: bold;
        }
       
        .questions-section {
            column-count: 2;
            column-gap: 15px;
            column-fill: balance;
            column-rule: 1px solid #ddd;
            margin-bottom: 20px;
        }
       
        .question {
            margin-bottom: 10px;
            break-inside: avoid;
            page-break-inside: avoid;
        }
       
        .question-header {
            margin-bottom: 4px;
            display: flex;
            align-items: flex-start;
        }
       
        .question-num {
            font-family: 'Times New Roman', serif;
            font-weight: bold;
            color: #000000;
            font-size: 12pt;
            margin-right: 5px;
            white-space: nowrap;
            flex-shrink: 0;
        }
       
        .question-text {
            flex: 1;
            line-height: 1.4;
            font-size: 12pt;
            color: #000000;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        /* Short options - 2x2 table */
        .options-table-short {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0 4px 8px;
            border: none;
        }
       
        .options-table-short td {
            border: none;
            padding: 2px 4px 2px 0;
            vertical-align: top;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 11pt;
            color: #000000;
            width: 50%;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        /* Long options - simple list */
        .options-list {
            margin: 4px 0 4px 8px;
            padding: 0;
            list-style: none;
        }
       
        .options-list li {
            margin: 2px 0;
            font-family: 'Noto Sans Bengali', 'SolaimanLipi', serif;
            font-size: 11pt;
            color: #000000;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: none;
        }
       
        .answer-key-section {
            margin-top: 20px;
            page-break-inside: avoid;
        }
       
        .answer-key-header {
            text-align: center;
            font-weight: bold;
            font-size: 13pt;
            margin-bottom: 10px;
            color: #000000;
        }
       
        .answer-key-table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #333;
            margin: 0 auto;
        }
       
        .answer-key-table th,
        .answer-key-table td {
            border: 1px solid #333;
            padding: 6px;
            text-align: center;
            font-size: 11pt;
        }
       
        .answer-key-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
       
        .answer-key-table td {
            font-weight: bold;
        }
       
        .qno-cell {
            width: 8%;
        }
       
        .ans-cell {
            width: 8%;
        }
       
        /* MathJax styling */
        mjx-container {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
            display: inline-block;
            margin: 0 1px;
            color: #000000;
        }
       
        mjx-container[jax="CHTML"] {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }
       
        .MathJax_Display {
            text-align: left !important;
            margin: 0.2em 0 !important;
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
        }
       
        img {
            max-width: 35% !important;
            height: auto !important;
            vertical-align: middle;
        }
       
        math {
            font-family: 'Cambria Math', 'Calibri Math', serif !important;
            font-size: 1em !important;
        }
       
        @media print {
            @page {
                size: A4 portrait;
                margin: 10mm 10mm;
            }
           
            body {
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
                width: 210mm;
                max-width: 210mm;
            }
           
            .question {
                break-inside: avoid;
                page-break-inside: avoid;
            }
           
            .answer-key-section {
                page-break-inside: avoid;
            }
           
            .questions-section {
                column-rule: 1px solid #ddd;
            }
        }
    </style>
</head>
<body>
    <div class="exam-header">
        <h1>{{ exam_name }}</h1>
    </div>
   
    <div class="questions-section">
        {% for question in questions %}
        <div class="question">
            <div class="question-header">
                <span class="question-num">{{ loop.index }}.</span>
                <div class="question-text">{{ question.question|safe }}</div>
            </div>
           
            {% if question.is_short_option %}
            <!-- Short options - 2x2 table -->
            <table class="options-table-short">
                <tr>
                    <td>(a) {{ question.options.A|safe }}</td>
                    <td>(b) {{ question.options.B|safe }}</td>
                </tr>
                <tr>
                    <td>(c) {{ question.options.C|safe }}</td>
                    <td>(d) {{ question.options.D|safe }}</td>
                </tr>
            </table>
            {% else %}
            <!-- Long options - simple list -->
            <ul class="options-list">
                <li>(a) {{ question.options.A|safe }}</li>
                <li>(b) {{ question.options.B|safe }}</li>
                <li>(c) {{ question.options.C|safe }}</li>
                <li>(d) {{ question.options.D|safe }}</li>
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
   
    <div class="answer-key-section">
        <div class="answer-key-header">সঠিক উত্তর যাচাই কর :)</div>
        <table class="answer-key-table">
            <thead>
                <tr>
                    <th class="qno-cell">প্রশ্ন</th>
                    {% for question in questions %}
                    <th class="qno-cell">{{ loop.index }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                <tr>
                    <th class="ans-cell">উত্তর</th>
                    {% for question in questions %}
                    <td class="ans-cell">{{ question.correct_answer }}</td>
                    {% endfor %}
                </tr>
            </tbody>
        </table>
    </div>
   
    <script>
        window.addEventListener('load', function() {
            if (typeof MathJax !== 'undefined') {
                MathJax.startup.promise.then(() => {
                    document.body.setAttribute('data-ready', 'true');
                    console.log('Format 3 ready for PDF generation');
                });
            } else {
                document.body.setAttribute('data-ready', 'true');
            }
        });
    </script>
</body>
</html>
'''
        template = Template(template_str)
        return template.render(questions=questions, exam_name=exam_name)
    
    def process_json_to_html(self, json_data: List[Dict[str, Any]], filename: str, format_type: int = 1, display_title: str = None) -> str:
        """Process JSON data to HTML"""
        try:
            # Normalize JSON format
            questions = self.normalize_json_format(json_data)
            
            if not questions:
                return ""
            
            # Prepare questions with format detection
            prepared_questions = self.prepare_questions(questions)
            
            # Get exam name (allow override)
            exam_name = display_title or self.get_exam_name_from_filename(filename)
            
            # Create HTML based on format
            if format_type == 1:
                html_content = self.create_format1_html(prepared_questions, exam_name)
            elif format_type == 2:
                html_content = self.create_format2_html(prepared_questions, exam_name)
            elif format_type == 3:
                html_content = self.create_format3_html(prepared_questions, exam_name)
            else:
                # Default to format 1
                html_content = self.create_format1_html(prepared_questions, exam_name)
            
            return html_content
            
        except Exception as e:
            print(f"Error processing JSON to HTML: {e}")
            return ""
