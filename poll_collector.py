#!/usr/bin/env python

# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Poll collector service based on PollBot class for collecting quiz polls and exporting to CSV/JSON.
"""

import os
import re
import csv
import json
import io
import tempfile
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

from telegram import Poll, Update, PollAnswer
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ContextTypes,
)
from bot.auth import check_authorization
# truncate_text utility - define locally if not available
def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_markdown(text: str) -> str:
    """
    Escape characters in text for MarkdownV2 formatting.
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


class PollBot:
    """
    Poll collector bot for collecting quiz polls and exporting to CSV/JSON.
    Adapted from https://github.com/XenonTheInertG/aio-bot/blob/main/poll_collector.py
    """

    def __init__(self, application: Application):
        self.application = application
        self.bot_token = application.bot.token
        self.user_states: Dict[int, Dict] = {}
        self.quiz_sessions: Dict[str, Dict] = {}
        self.MAX_POLLS = 200
        self.MAX_CSV_SIZE = 10 * 1024 * 1024
        self.POLL_DELAY = 6
        self.MAX_CSV_ROWS = 500
        # Quiz session control - per-chat lock to guarantee sequential polls
        self.active_quiz_locks: Dict[str, asyncio.Lock] = {}

    # ===== CSV Collector =====
    
    async def handle_csv_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /csv command to start collecting polls"""
        user_id = update.effective_user.id
        if user_id in self.user_states and self.user_states[user_id].get('is_collecting', False):
            await update.message.reply_text(
                f"❌ You're already collecting polls!\nCurrent progress: {len(self.user_states[user_id]['polls'])}/{self.MAX_POLLS}\nUse `/done` or `/cancel`.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        filename = self.parse_filename(update.message.text)
        self.user_states[user_id] = {
            'is_collecting': True,
            'polls': [],
            'filename': filename,
            'start_time': datetime.now(),
            'last_progress_message_id': None,
            'pending_polls': [],
            'processing_task': None,
            'chat_id': update.effective_chat.id,
        }

        await update.message.reply_text(
            f"✅ **Started collecting polls!**\n\n📁 **Filename:** `{filename}`\n📊 Send your polls, and I'll show progress after processing all of them.",
            parse_mode=ParseMode.MARKDOWN,
        )

    def parse_filename(self, command_text: str) -> str:
        """Parse filename from command text"""
        match = re.search(r'-n\s+"([^"]+)"', command_text)
        if match:
            filename = match.group(1).strip()
            if not filename.endswith('.csv'):
                filename += '.csv'
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            return filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"polls_{timestamp}.csv"

    async def handle_done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /done command to finish collection or merge."""
        user_id = update.effective_user.id
        user_session = context.user_data.get(user_id, {})

        if user_session.get('is_merging'):
            await self.perform_merge(update, context)
            return

        if user_id not in self.user_states or not self.user_states[user_id].get('is_collecting', False):
            await update.message.reply_text("❌ You're not collecting polls. Use `/csv` to start.")
            return

        user_state = self.user_states[user_id]
        # Cancel any pending processing task
        if user_state.get('processing_task') and not user_state['processing_task'].done():
            user_state['processing_task'].cancel()

        polls_count = len(user_state['polls'])
        if polls_count == 0:
            await update.message.reply_text("❌ No valid polls collected. Send polls with correct answers.")
            return

        filename = user_state['filename']

        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as tmp:
                await self.generate_csv(user_state['polls'], tmp.name)
                await update.message.reply_document(
                    document=open(tmp.name, 'rb'),
                    caption=f"📊 **Poll Collection Complete!**\n\n📁 **File:** `{filename}`\n📈 **Total Polls:** {polls_count}\n⏱️ **Time:** {self.get_duration(user_state['start_time'])}",
                    parse_mode=ParseMode.MARKDOWN,
                    filename=filename
                )
            os.unlink(tmp.name)
            await self.cleanup_progress_message(update.effective_chat.id, user_state, context)
            user_state['is_collecting'] = False
            user_state['last_progress_message_id'] = None
        except Exception as e:
            await update.message.reply_text(f"❌ Error generating CSV: {str(e)}")

    async def handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Shows the current status of the poll collection."""
        user_id = update.effective_user.id
        if user_id not in self.user_states or not self.user_states[user_id].get('is_collecting', False):
            await update.message.reply_text("❌ You're not collecting polls. Use `/csv` to start.")
            return

        user_state = self.user_states[user_id]
        polls_count = len(user_state['polls'])
        pending_count = len(user_state['pending_polls'])
        progress_bar = self.create_progress_bar(polls_count, self.MAX_POLLS)
        await update.message.reply_text(
            f"📊 **Collection Status**\n\n📁 **Filename:** `{user_state['filename']}`\n📈 **Processed:** {polls_count}/{self.MAX_POLLS}\n📥 **Pending:** {pending_count}\n{progress_bar}\n⏱️ **Duration:** {self.get_duration(user_state['start_time'])}",
            parse_mode=ParseMode.MARKDOWN,
        )

    @check_authorization
    async def handle_cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command to cancel collection or merge."""
        user_id = update.effective_user.id
        user_session = context.user_data.get(user_id, {})

        if user_session.get('is_merging'):
            # Cleanup for merge session
            for file_path in user_session.get('merge_files', []):
                if os.path.exists(file_path):
                    os.remove(file_path)
            context.user_data[user_id] = {}
            await update.message.reply_text("❌ **Merge session cancelled.**")
            return

        if user_id not in self.user_states or not self.user_states[user_id].get('is_collecting', False):
            await update.message.reply_text("❌ You're not in an active session.")
            return

        user_state = self.user_states[user_id]
        polls_count = len(user_state['polls'])
        if user_state.get('processing_task') and not user_state['processing_task'].done():
            user_state['processing_task'].cancel()

        await self.cleanup_progress_message(update.effective_chat.id, user_state, context)
        user_state['is_collecting'] = False
        user_state['last_progress_message_id'] = None
        await update.message.reply_text(
            f"❌ **Collection cancelled!**\n\n📊 **Polls discarded:** {polls_count}\n\nStart a new collection with `/csv`.",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ===== Merge Feature =====
    
    @check_authorization
    async def handle_merge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Starts a file merging session."""
        user_id = update.effective_user.id
        filename_match = re.search(r'"([^"]+)"', update.message.text)
        filename = filename_match.group(1).strip() if filename_match else None

        context.user_data[user_id] = {
            'is_merging': True,
            'merge_files': [],
            'merge_mode': None,  # 'csv' or 'json'
            'merge_filename': filename
        }
        await update.message.reply_text("📁 **Merge Mode Started!**\n\n📤 Send files to merge (all CSV or all JSON).\n✅ Type /done when finished.")

    async def perform_merge(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Performs the file merge and sends the result."""
        user_id = update.effective_user.id
        user_session = context.user_data.get(user_id, {})

        if not user_session.get('merge_files'):
            await update.message.reply_text("❌ No files to merge. Use /merge to start.")
            return

        progress_msg = await update.message.reply_text("🔄 Merging files...")
        merge_files = user_session['merge_files']
        merge_mode = user_session['merge_mode']
        output_filename = user_session.get('merge_filename')

        try:
            if merge_mode == 'csv':
                if not output_filename:
                    output_filename = "merged.csv"
                elif not output_filename.endswith('.csv'):
                    output_filename += ".csv"

                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as tmp:
                    # Read header from the first file
                    with open(merge_files[0], 'r', encoding='utf-8-sig') as f:
                        header = f.readline()
                        tmp.write(header)
                        for line in f:
                            tmp.write(line)

                    # Read subsequent files, skipping their headers
                    for file_path in merge_files[1:]:
                        with open(file_path, 'r', encoding='utf-8-sig') as f:
                            f.readline() # Skip header
                            for line in f:
                                tmp.write(line)

                    await update.message.reply_document(document=open(tmp.name, 'rb'), filename=output_filename)
                os.unlink(tmp.name)

            elif merge_mode == 'json':
                if not output_filename:
                    output_filename = "merged.json"
                elif not output_filename.endswith('.json'):
                    output_filename += ".json"

                combined_json = []
                for file_path in merge_files:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            combined_json.extend(data)
                        else:
                            combined_json.append(data)

                json_str = json.dumps(combined_json, ensure_ascii=False, indent=2)
                output_file = io.BytesIO(json_str.encode('utf-8'))
                await update.message.reply_document(output_file, filename=output_filename)

            await progress_msg.edit_text(f"✅ **Merge Complete!**\n📁 Files merged: {len(merge_files)}")

        except Exception as e:
            await update.message.reply_text(f"❌ Merge failed: {str(e)}")
        finally:
            # Cleanup
            for file_path in merge_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            context.user_data[user_id] = {} # Clear session

    # ===== ENHANCED QUIZ SESSION =====
    
    def parse_quiz_arguments(self, command_text: str) -> Dict[str, str]:
        args = {}
        m_match = re.search(r'-m\s+"([^"]+)"', command_text)
        if m_match:
            args['m'] = m_match.group(1)
        c_match = re.search(r'-c\s+"?(-?\d+)"?', command_text)
        if c_match:
            args['c'] = int(c_match.group(1))
        t_match = re.search(r'-t\s+(\d+)', command_text)
        if t_match:
            args['t'] = int(t_match.group(1))
        return args

    @check_authorization
    async def handle_quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Must reply to CSV/JSON
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("❌ Please reply to a CSV or JSON file with `/quiz`")
            return

        args = self.parse_quiz_arguments(update.message.text)
        open_period = args.get('t', 10)
        target_chat_id = args.get('c', update.effective_chat.id)
        announce_text = args.get('m', "🎯 Quiz Starting!")

        # Validate file
        document = update.message.reply_to_message.document
        ext = document.file_name.lower().rsplit('.', 1)[-1]
        if ext not in ("csv", "json"):
            await update.message.reply_text("❌ File must be CSV or JSON")
            return

        # Download
        processing_msg = await update.message.reply_text("📥 *Processing quiz file\\.\\.\\.*", parse_mode=ParseMode.MARKDOWN_V2)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            file = await context.bot.get_file(document.file_id)
            await file.download_to_drive(tmp.name)

            # Load questions
            if ext == "csv":
                questions = await self.load_quiz_from_csv(tmp.name)
            else:
                questions = await self.load_quiz_from_json(tmp.name)

        try:
            os.unlink(tmp.name)
        except: pass

        if not questions:
            await processing_msg.edit_text("❌ *No valid questions found in file*", parse_mode=ParseMode.MARKDOWN_V2)
            return

        # Create session
        session_id = f"{target_chat_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.quiz_sessions[session_id] = {
            'chat_id': target_chat_id,
            'questions': questions,
            'user_scores': {},
            'current_question': 0,
            'open_period': open_period,
            'start_time': datetime.utcnow(),
            'lock': self.active_quiz_locks.setdefault(str(target_chat_id), asyncio.Lock()),
        }

        await processing_msg.edit_text(
            f"✅ *Quiz started\\!* {len(questions)} questions @ {open_period}s each",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Run quiz
        await self.run_quiz_sequence(session_id, context)

    async def run_quiz_sequence(self, session_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.quiz_sessions.get(session_id)
        if not session:
            return
        async with session['lock']:
            total = len(session['questions'])
            while session['current_question'] < total:
                await self.send_question(session_id, context)
                await asyncio.sleep(session['open_period'] + 1)
                session['current_question'] += 1
            await self.finish_quiz(session_id, context)

    async def send_question(self, session_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.quiz_sessions[session_id]
        idx = session['current_question']
        total = len(session['questions'])
        q = session['questions'][idx]

        header = f"[{idx+1}/{total}] "
        question_text = header + q['question']

        options = [f"{opt['letter']}. {opt['text']}" for opt in q['options']]
        correct_idx = next((i for i,opt in enumerate(q['options']) if opt['letter']==q['correct_answer']), None)
        if correct_idx is None:
            return

        explanation = truncate_text(q.get('explanation', ''), 200)

        msg = await context.bot.send_poll(
            chat_id=session['chat_id'],
            question=question_text,
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_idx,
            is_anonymous=False,
            open_period=session['open_period'],
            explanation=explanation
        )
        poll_id = msg.poll.id
        context.bot_data[poll_id] = {
            'session_id': session_id,
            'correct_answer': q['correct_answer'],
            'options': q['options']
        }

    async def handle_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        answer = update.poll_answer
        data = context.bot_data.get(answer.poll_id)
        if not data: return
        session = self.quiz_sessions.get(data['session_id'])
        if not session: return

        user = answer.user
        sel = answer.option_ids[0] if answer.option_ids else None
        letter = data['options'][sel]['letter'] if sel is not None and sel < len(data['options']) else None
        correct = (letter == data['correct_answer'])

        scores = session['user_scores'].setdefault(user.id, {
            'name': user.full_name,
            'username': user.username or "",
            'correct': 0,
            'wrong': 0,
            'score': 0.0
        })
        if correct:
            scores['correct'] += 1
            scores['score'] += 1.0
        else:
            scores['wrong'] += 1
            scores['score'] -= 0.25

    async def finish_quiz(self, session_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.quiz_sessions.pop(session_id, None)
        if not session: return

        chat_id = session['chat_id']
        scores = list(session['user_scores'].values())
        scores.sort(key=lambda x: (x['score'], x['correct']), reverse=True)

        total_q = len(session['questions'])
        dur = datetime.utcnow() - session['start_time']
        mins, secs = divmod(int(dur.total_seconds()), 60)

        lines = [
            "*🏁 Quiz Finished\\!*",
            f"*Questions:* {total_q}",
            f"*Duration:* {mins}m {secs}s",
            f"*Participants:* {len(scores)}",
            "",
            "*🏆 Leaderboard 🏆*",
            ""
        ]
        if not scores:
            lines.append("_No participants_")
        else:
            medals = ["🥇","🥈","🥉"]
            for i, p in enumerate(scores[:15]):
                if i < 3:
                    rank = medals[i]
                else:
                    rank = f"{i+1}\\."
                name = escape_markdown(p['username'] and f"@{p['username']}" or p['name'])
                lines.append(f"{rank} *{name}*")
                score_str = f"{p['score']:.2f}".replace('.', '\\.').replace('-', '\\-')
                lines.append(f"   Score: {score_str} \\(✓{p['correct']} ✗{p['wrong']}\\)")
                lines.append("")

        text = "\n".join(lines)
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)

    # ===== CSV/JSON Loading =====
    
    async def load_quiz_from_csv(self, csv_path: str) -> List[Dict]:
        """Load quiz questions from CSV file with robust parsing"""
        questions = []
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(csv_path, 'r', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    if not reader.fieldnames:
                        continue
                    
                    # Create case-insensitive field mapping
                    field_mapping = {}
                    for field in reader.fieldnames:
                        lower_field = field.lower().strip()
                        if lower_field == 'questions':
                            field_mapping['questions'] = field
                        elif lower_field == 'answer':
                            field_mapping['answer'] = field
                        elif lower_field == 'explanation':
                            field_mapping['explanation'] = field
                        elif lower_field.startswith('option'):
                            field_mapping[lower_field] = field
                    
                    # Check required fields
                    if 'questions' not in field_mapping or 'answer' not in field_mapping:
                        continue
                    
                    for row in reader:
                        question_text = (row.get(field_mapping.get('questions', '')) or '').strip()
                        if not question_text:
                            continue
                        
                        # Extract options
                        options = []
                        option_letters = ['A', 'B', 'C', 'D', 'E']
                        for i, letter in enumerate(option_letters, start=1):
                            option_key = f'option{i}'
                            option_text = (row.get(field_mapping.get(option_key, '')) or '').strip()
                            if option_text:
                                options.append({'letter': letter, 'text': option_text})
                        
                        if len(options) < 2:
                            continue
                        
                        # Get correct answer
                        answer_text = (row.get(field_mapping.get('answer', '')) or '').strip()
                        try:
                            correct_idx = int(answer_text) - 1
                            if not (0 <= correct_idx < len(options)):
                                continue
                            correct_letter = options[correct_idx]['letter']
                        except (ValueError, TypeError):
                            continue
                        
                        explanation = (row.get(field_mapping.get('explanation', '')) or '').strip()
                        
                        questions.append({
                            'question': question_text,
                            'options': options,
                            'correct_answer': correct_letter,
                            'explanation': explanation
                        })
                    
                    return questions
                    
            except (UnicodeDecodeError, Exception) as e:
                continue
        
        return questions

    async def load_quiz_from_json(self, json_path: str) -> List[Dict]:
        """Load quiz questions from JSON file"""
        questions = []
        try:
            with open(json_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
            
            if not isinstance(data, list):
                return questions
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                question_text = str(item.get('question', '')).strip()
                options_data = item.get('options', {})
                
                if not question_text or not isinstance(options_data, dict):
                    continue
                
                # Extract options
                options = []
                for letter in ['A', 'B', 'C', 'D', 'E']:
                    option_text = options_data.get(letter)
                    if option_text:
                        options.append({'letter': letter, 'text': str(option_text)})
                
                if len(options) < 2:
                    continue
                
                # Validate correct answer
                correct_answer = str(item.get('correct_answer', '')).strip().upper()
                if correct_answer not in [opt['letter'] for opt in options]:
                    continue
                
                explanation = str(item.get('explanation', '')).strip()
                
                questions.append({
                    'question': question_text,
                    'options': options,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })
            
        except Exception as e:
            pass
        
        return questions

    # ===== File Operations =====
    
    @check_authorization
    async def handle_convert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Convert JSON file to CSV format"""
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("❌ Please reply to a JSON file with `/convert`")
            return
        
        document = update.message.reply_to_message.document
        if not document.file_name.lower().endswith('.json'):
            await update.message.reply_text("❌ Please reply to a JSON file")
            return
        
        # Parse filename from command
        filename_match = re.search(r'-n\s+"([^"]+)"', update.message.text)
        if filename_match:
            csv_filename = filename_match.group(1).strip()
            if not csv_filename.endswith('.csv'):
                csv_filename += '.csv'
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"converted_{timestamp}.csv"
        
        csv_filename = re.sub(r'[<>:"/\\|?*]', '_', csv_filename)
        
        try:
            processing_msg = await update.message.reply_text("🔄 **Converting JSON to CSV...**")

            file = await context.bot.get_file(document.file_id)
            json_content_bytes = await file.download_as_bytearray()
            json_content = json_content_bytes.decode('utf-8-sig')  # Use utf-8-sig to handle potential BOM
            json_data = json.loads(json_content)

            if not json_data:
                await processing_msg.edit_text("❌ **Error:** JSON file appears to be empty.")
                return

            csv_data = self.json_to_csv(json_data)
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8', newline='') as csv_tmp:
                csv_tmp.write(csv_data)
                csv_tmp.seek(0)  # Move cursor to the beginning of the file before reading
                await processing_msg.edit_text("✅ **Conversion complete!**")
                await update.message.reply_document(
                    document=open(csv_tmp.name, 'rb'),
                    filename=csv_filename,
                    caption=f"📁 **Converted File:** `{csv_filename}`\n📊 **Questions:** {len(json_data)}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            os.unlink(csv_tmp.name)
            
        except json.JSONDecodeError:
            await processing_msg.edit_text("❌ **Error:** Invalid JSON format. Please check your file.")
        except Exception as e:
            await processing_msg.edit_text(f"❌ An unexpected error occurred during conversion.")
            import traceback
            traceback.print_exc()

    def json_to_csv(self, questions: List[Dict]) -> str:
        """Convert JSON questions to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(["questions", "option1", "option2", "option3", "option4", "option5", "answer", "explanation", "type", "section"])
        
        answer_map = {'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5'}
        
        for question in questions:
            options = question.get('options', {})
            row = [
                question.get('question', ''),
                options.get('A', ''),
                options.get('B', ''),
                options.get('C', ''),
                options.get('D', ''),
                options.get('E', ''),
                answer_map.get(question.get('correct_answer', ''), ''),
                question.get('explanation', ''),
                '1',
                '1',
            ]
            writer.writerow(row)
        
        return output.getvalue()

    def csv_to_json(self, csv_content: str) -> List[Dict]:
        """Converts CSV content to a JSON-compatible list of dictionaries."""
        questions = []
        reader = csv.reader(io.StringIO(csv_content))
        next(reader)  # Skip header
        option_keys = ['A', 'B', 'C', 'D', 'E']
        answer_map = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E'}
        for row in reader:
            if len(row) < 7:  # Ensure there are enough columns for question, options, and answer
                continue
            question = row[0]
            options = {option_keys[i]: row[i+1] for i in range(5) if len(row) > i+1 and row[i+1]}
            answer = answer_map.get(row[6], '')
            explanation = row[7] if len(row) > 7 else ""

            if question:
                questions.append({
                    'question': question,
                    'options': options,
                    'correct_answer': answer,
                    'explanation': explanation
                })
        return questions

    @check_authorization
    async def handle_convert2_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Convert CSV file to JSON format."""
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("❌ Please reply to a CSV file with `/convert2`")
            return

        document = update.message.reply_to_message.document
        if not document.file_name.lower().endswith('.csv'):
            await update.message.reply_text("❌ Please reply to a CSV file")
            return

        try:
            processing_msg = await update.message.reply_text("🔄 **Converting CSV to JSON...**")

            file = await context.bot.get_file(document.file_id)
            csv_content_bytes = await file.download_as_bytearray()
            csv_content = csv_content_bytes.decode('utf-8-sig')

            json_data = self.csv_to_json(csv_content)
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
            output_file = io.BytesIO(json_str.encode('utf-8'))
            json_filename = os.path.splitext(document.file_name)[0] + ".json"

            await processing_msg.edit_text("✅ **Conversion complete!**")

            await update.message.reply_document(
                document=output_file,
                filename=json_filename,
                caption=f"📁 **Converted File:** `{json_filename}`\n📊 **Questions:** {len(json_data)}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error converting file: {str(e)}")

    @check_authorization
    async def handle_rename_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Rename a file by downloading and re-uploading with new name"""
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("❌ Please reply to a file with `/rename \"newname\"`")
            return
        
        filename_match = re.search(r'"([^"]+)"', update.message.text)
        if not filename_match:
            await update.message.reply_text('❌ Please provide a new filename in quotes: `/rename "newname"`')
            return
        
        new_filename = filename_match.group(1).strip()
        document = update.message.reply_to_message.document
        original_ext = document.file_name.split('.')[-1] if '.' in document.file_name else ''
        
        if original_ext and not new_filename.endswith(f'.{original_ext}'):
            new_filename += f'.{original_ext}'
        
        new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename)
        
        try:
            processing_msg = await update.message.reply_text("🔄 **Renaming file...**")

            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{original_ext}' if original_ext else '') as tmp:
                file = await context.bot.get_file(document.file_id)
                await file.download_to_drive(tmp.name)

                await processing_msg.edit_text("✅ **File renamed!**")

                await update.message.reply_document(
                    document=open(tmp.name, 'rb'),
                    filename=new_filename,
                    caption=f"📁 **New filename:** `{new_filename}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            os.unlink(tmp.name)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error renaming file: {str(e)}")

    # ===== Poll Collection Handlers =====
    
    async def handle_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming polls for collection"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or not self.user_states[user_id].get('is_collecting', False):
            return
        
        user_state = self.user_states[user_id]
        if len(user_state['polls']) >= self.MAX_POLLS:
            await update.message.reply_text(f"❌ **Limit reached!** ({self.MAX_POLLS})\nUse `/done` to generate CSV.")
            return
        
        try:
            poll_data = self.extract_poll_data(update)
            if not poll_data['answer']:
                await update.message.delete()
                return
            
            user_state['pending_polls'].append((update.message, poll_data))
            
            if user_state.get('processing_task') is None or user_state['processing_task'].done():
                user_state['processing_task'] = asyncio.create_task(self.process_pending_polls(user_id))
            
            await update.message.delete()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            await update.message.reply_text("❌ Error processing poll.")

    async def process_pending_polls(self, user_id: int):
        """Process pending polls after a short delay"""
        user_state = self.user_states.get(user_id)
        if not user_state:
            return
        
        await asyncio.sleep(2)  # Wait to collect batch
        
        if not user_state['pending_polls']:
            return
        
        last_poll_data = None
        for message_obj, poll_data_item in user_state['pending_polls']:
            if len(user_state['polls']) >= self.MAX_POLLS:
                break
            user_state['polls'].append(poll_data_item)
            last_poll_data = poll_data_item
        
        user_state['pending_polls'] = []
        polls_count = len(user_state['polls'])
        progress_bar = self.create_progress_bar(polls_count, self.MAX_POLLS)
        
        last_question_text = ""
        if last_poll_data and last_poll_data.get('questions'):
            last_question = last_poll_data['questions']
            last_question_text = f"📝 **Last Question:** {last_question[:50]}{'...' if len(last_question) > 50 else ''}\n"
        
        progress_text = (
            f"✅ **Polls processed: {polls_count}/{self.MAX_POLLS}**\n"
            f"{progress_bar}\n\n"
            f"{last_question_text}"
            f"Send more polls or use `/done` to finish."
        )
        
        chat_id_to_use = user_state.get('chat_id')
        if not chat_id_to_use:
            return
        
        # Update or send progress message
        if user_state.get('last_progress_message_id'):
            try:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id_to_use,
                    message_id=user_state['last_progress_message_id'],
                    text=progress_text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                progress_message = await self.application.bot.send_message(chat_id_to_use, progress_text, parse_mode=ParseMode.MARKDOWN)
                user_state['last_progress_message_id'] = progress_message.message_id
        else:
            progress_message = await self.application.bot.send_message(chat_id_to_use, progress_text, parse_mode=ParseMode.MARKDOWN)
            user_state['last_progress_message_id'] = progress_message.message_id
        
        if polls_count >= self.MAX_POLLS:
            await self.application.bot.send_message(
                chat_id=chat_id_to_use,
                text=f"🎉 **Maximum polls collected!** ({self.MAX_POLLS})\nUse `/done` to generate CSV.",
                parse_mode=ParseMode.MARKDOWN,
            )

    def extract_poll_data(self, update: Update) -> Dict[str, str]:
        """Extract data from a poll message"""
        poll = update.message.poll
        if not poll:
            raise ValueError("Invalid poll message")
        
        question = self.remove_tags(poll.question) or "Unknown Question"
        options = [self.remove_tags(opt.text) if opt.text else "" for opt in poll.options]
        
        # Pad options to 5
        while len(options) < 5:
            options.append('')
        
        correct_answer = ''
        if poll.correct_option_id is not None:
            correct_answer = str(poll.correct_option_id + 1)
        
        explanation = self.get_poll_explanation(update)
        
        return {
            'questions': question,
            'option1': options[0],
            'option2': options[1],
            'option3': options[2],
            'option4': options[3],
            'option5': options[4],
            'answer': correct_answer,
            'explanation': explanation,
            'type': '1',
            'section': '1'
        }

    def get_poll_explanation(self, update: Update) -> str:
        """Get explanation from poll"""
        explanation = ""
        if update.message.poll and update.message.poll.explanation:
            explanation = self.remove_tags(update.message.poll.explanation)
        return explanation

    def remove_tags(self, text: str) -> str:
        """Remove unwanted tags and patterns from text"""
        if not text:
            return ''
        
        # Various cleaning patterns
        question_number_patterns = [
            r'^\d+[.\)]\s*',
            r'^[০১২৩৪৫৬৭৮৯]+[।)]\s*',
            r'^\(\d+\)\s*',
            r'^\([০১২৩৪৫৬৭৮৯]+\)\s*',
        ]
        
        bracket_patterns = [
            r'\[.*?\]', r'\{.*?\}', r'【.*?】', r'〖.*?〗', r'〔.*?〕', r'\(.*?\)'
        ]
        
        tag_patterns = [
            r'\b(?:SSP|ssp|Remedics|REMEDICS|remedics|Fighters|FIGHTERS|fighters|Medical|MEDICAL|medical|Academy|ACADEMY|academy|Test|TEST|test|Mock|MOCK|mock|Exam|EXAM|exam|Quiz|QUIZ|quiz|Practice|PRACTICE|practice)\b',
            r'\b(?:হাজারী|গুহ)\s*স্যার\b',
            r'\b(?:পৃ-\d+\b.*?)(?=\s|$)',
            r'\b(?:মেডিকেল|উন্মেষ|মাস্টার|প্রশ্নব্যাংক|প্র্যাকটিস|বুক)\b',
        ]
        
        cleaned_text = text
        for pattern in question_number_patterns + bracket_patterns + tag_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        # Clean up whitespace and bullets
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = re.sub(r'^\s*[-•·*]\s*', '', cleaned_text)
        cleaned_text = re.sub(r'\s*[-•·*]\s*$', '', cleaned_text)
        
        return cleaned_text.strip()

    # ===== Utility Functions =====
    
    async def generate_csv(self, polls: List[Dict], filename: str):
        """Generate CSV file from collected polls"""
        fieldnames = [
            'questions', 'option1', 'option2', 'option3', 'option4',
            'option5', 'answer', 'explanation', 'type', 'section'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for poll in polls:
                writer.writerow(poll)

    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a visual progress bar"""
        filled = int(length * current / total) if total else 0
        filled = max(0, min(length, filled))
        bar = '█' * filled + '░' * (length - filled)
        percentage = (current / total) * 100 if total else 0
        percentage_str = f"{percentage:.1f}".replace('.', '\\.')
        return f"[{bar}] {percentage_str}%"

    def get_duration(self, start_time: datetime) -> str:
        """Format duration from start time"""
        duration = datetime.now() - start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    async def cleanup_progress_message(self, chat_id: int, user_state: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Clean up progress message"""
        if user_state.get('last_progress_message_id'):
            try:
                await context.bot.delete_message(chat_id, user_state['last_progress_message_id'])
            except Exception:
                pass


# Global instance - will be initialized with application
_poll_bot_instance: Optional[PollBot] = None


def get_poll_bot(application: Application = None) -> Optional[PollBot]:
    """Get or create the poll bot instance"""
    global _poll_bot_instance
    if _poll_bot_instance is None:
        if application is not None:
            _poll_bot_instance = PollBot(application)
        else:
            return None
    return _poll_bot_instance


def init_poll_bot(application: Application) -> PollBot:
    """Initialize the poll bot with application"""
    global _poll_bot_instance
    _poll_bot_instance = PollBot(application)
    return _poll_bot_instance

