# Telegram Quiz Bot 🎯

A powerful Telegram bot that converts images and PDFs into interactive quizzes with automatic answer detection, AI-powered suggestions, and multi-language explanations. Designed for educational use, this bot supports Bengali textbook questions, MBBS medical MCQs, and standard quiz processing.

## Features ✨

- **Image to Quiz Conversion**: Convert images containing questions and answer keys into interactive Telegram quizzes
- **PDF Processing**: Process PDF files with page range selection, convert pages to images automatically
- **Automatic Answer Detection**:
  - 🔍 Automatically detects correct answers from answer keys at the bottom of exam papers
  - 🎯 Works with multiple formats, including answer grids and individual answer notations
- **AI-Powered Features**:
  - 💡 AI-suggested answers (with confidence scores) when automatic detection isn't possible
  - 🧠 Multi-language explanations for each answer (Bengali, English)
  - 🔑 Multi-key support with automatic failover and load balancing
- **Bengali Textbook Mode**:
  - 📚 Generate Bengali MCQs directly from textbook images
  - 🇧🇩 Perfect for creating educational content in Bengali
  - 🎓 Supports biology, physics, chemistry, and manobik gunaboli (ethics)
  - 📝 Creates multiple high-quality Bengali MCQs per image with explanations
- **MBBS Mode**:
  - 🏥 Generate medical MCQs for MBBS students
  - 📖 Covers all MBBS subjects: Anatomy, Physiology, Pathology, Pharmacology, etc.
  - 🎯 Includes clinical scenarios and USMLE/PLAB-style questions
  - 💊 Creates medical MCQs with detailed explanations
- **Batch Processing**:
  - 🚀 "Send All Quizzes" button to automatically send multiple quizzes at once
  - ⏱️ Progress tracking for batch sending
- **Multi-Image Handling**:
  - 📊 Process multiple images sent together in one go
  - 🔄 Combines questions from all images into a single batch
  - 📋 Shows detailed progress for each image being processed
- **Multiple Subjects**: Organize quizzes by subjects (Biology, Physics, Chemistry, Math, English, General Knowledge)
- **Flexible Delivery Options**:
  - 📑 Topic Mode: Send quizzes to specific forum topics
  - 📢 Channel Mode: Send quizzes to a designated channel
  - 🔄 Dual Mode: Send to both topic and channel simultaneously
- **Topic Management**:
  - Create new topics by name
  - Use existing topics by name
  - Set topics directly using numeric IDs
  - Automatic similar topic detection
- **Quiz Management**:
  - Edit questions and options with conversational interface
  - Preview explanations before posting
  - Remove questions from the queue
  - Copy quiz text for sharing elsewhere
  - No individual quiz previews - only bulk action buttons for cleaner interface
- **Interactive Settings**: Easy-to-use settings menu to configure:
  - Delivery mode (Topic/Channel/Dual)
  - Topic selection (by name or ID)
  - Explanation toggle (on/off)
  - Bengali Textbook Mode toggle
  - MBBS Mode toggle
  - Exam Tag Mode toggle
  - Poll Collection Mode toggle

## Technical Details 🔧

- **AI Integration**: Uses Google Gemini 2.5 Flash for:
  - Question and answer extraction from images
  - Answer prediction when automatic detection fails
  - Bengali explanations with intelligent cleaning to avoid metadata text
  - Medical MCQ generation for MBBS mode
  - Bengali MCQ generation for textbook mode
  - Multi-key support with automatic rotation and health monitoring
- **Telegram API**: Built with python-telegram-bot library for robust API integration
- **Error Handling**: Comprehensive system to handle message length limits, rate limiting, and other Telegram constraints
- **Dynamic Content Formatting**: Automatically truncates content to stay within Telegram's message limits
- **Clean Explanation Generation**: Filters out garbage text like character counts and metadata references
- **Media Group Handling**: Intelligent detection and processing of multiple images sent as a group
- **PDF to Quiz**:
  - 📄 Convert selected PDF pages into quizzes (enter a page range like `1-10`)
  - 🌐 For large PDFs (>20MB), automatically uses Pyrogram user account for download
  - 🔗 For very large files, send an http/https link; the bot downloads and processes without size limits
  - 📦 Supports files up to 2GB when using user account credentials
- **CSV/JSON Import & Export**:
  - ⬇️ Import CSV/JSON files to auto-send quizzes as Telegram polls (no review screen)
  - ⬆️ Export current quiz data to CSV/JSON with the requested schema
  - CSV schema: `question, option1..option5, answer (1-5), explination`
- **PDF Export**:
  - 📄 Export generated quizzes to professionally formatted PDFs
  - Two formats: Practice Sheet (with answers inline) and Question Answer Sheet (separate sections)
  - A4 size, MathJax support, Bengali font rendering
  - Available from quiz results UI or settings menu
- **Poll Collection to CSV**:
  - 📥 Collect forwarded or direct quiz polls
  - 💾 Send "done" to export all collected polls into one CSV
  - ✏️ Status message editing (no message spam - updates existing message)
- **Custom Prompt Mode (`/gen` command)**:
  - 🧩 Generate custom quizzes with user-defined prompts
  - 📝 Use `/gen` command with your instructions (e.g., `/gen সত্যু মিথ্যা প্রশ্ন বানিয়ে দাও, ২০টা প্রশ্ন বানিয়ে দাও`)
  - 🖼️ Works with images (reply to image or use last sent image)
  - 🎯 Perfect for creating specific question types or styles
- **Large File Download Support**:
  - 📦 Download PDFs up to 2GB using Pyrogram user account
  - 🔄 Automatic fallback to bot token for smaller files
  - ⚡ Seamless integration with existing PDF processing
- **Performance Optimizations**:
  - 🚀 Optimized for multiple concurrent users
  - ⚡ Configurable connection pools and thread workers
  - 📊 Better resource management for high-traffic scenarios
- **Exam Tag Controls**:
  - 🏷️ Preserve exam tags from images and optionally append a custom tag when enabled
  - 🧹 When disabled, remove actual exam tags while preserving other bracketed text and `QUIZ_MARKER`
  - ✨ Enhanced cleanup handles complex tags including:
    - Ordinal numbers (35th, 36th, etc.)
    - BCS and other exam codes
    - Bengali text in tags
    - Comma-separated tag content
    - Long university codes and ministry names
- **Pinned Header**:
  - 📌 Before sending quizzes, the bot posts “Quiz by user <user_id>” and pins it in the destination
- **PDF Rendering**: Uses PyMuPDF (`pymupdf`) to convert PDF pages to images via a background thread
- **System Monitoring**: Comprehensive system metrics via `/status` or `/logs`:
  - CPU usage, frequency, load averages, and per-core statistics
  - Memory usage (RAM and swap) with detailed breakdowns
  - Disk usage, I/O rates, and operation counts
  - Network statistics, upload/download speeds, ping latency
  - Network interface information (IP addresses, speeds, MTU)
  - Process-specific metrics (memory, CPU, threads, open files)
  - System temperature sensors (if available)
  - Boot time and system uptime tracking
  - Real-time I/O rates for disk and network

## Setup 🚀

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browser (required for PDF export):
   ```bash
   python -m playwright install --with-deps chromium
   ```
4. Create a `.env` file with the following variables (or copy from `.env_example`):
   ```env
   # API Keys & Tokens (required)
   BOT_TOKEN=your_telegram_bot_token
   GEMINI_API_KEY=your_google_gemini_api_key

   # MongoDB (required for DB-backed settings)
   MONGODB_URI=mongodb+srv://username:password@host/dbname?retryWrites=true&w=majority
   MONGODB_DB=tss_bot

   # Pyrogram User Account (optional - for files >20MB)
   # Get from https://my.telegram.org/apps
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   # Session string (required for GitHub Actions/CI - see README for generation)
   TELEGRAM_SESSION_STRING=your_session_string

   # Multi-Key Support (Optional - For Enhanced Reliability)
   GEMINI_API_KEYS=key1,key2,key3

   # Initial seed values (optional; configurable later via /db)
   CHANNEL_ID=your_channel_id
   GROUP_ID=your_group_id
   QUIZ_MARKER=[Your Quiz Prefix]
   EXPLANATION_MODE=on  # or 'off'
   QUIZ_EXPLANATION_LINK=👨‍🏫 t.me/YourChannel
   AUTHORIZED_USERS=comma_separated_user_ids

   # Performance & Concurrency (optional)
   MAX_CONCURRENT_USERS=100
   THREAD_POOL_WORKERS=20
   CONNECTION_POOL_SIZE=100
   MAX_PARALLEL_PAGES=4
   ```

### Multi-Key Configuration 🔑

The bot now supports multiple Gemini API keys for enhanced reliability and performance:

- **Automatic Failover**: If one key fails, the bot automatically switches to the next available key
- **Load Balancing**: Distributes requests across multiple keys to avoid rate limits
- **Health Monitoring**: Tracks key performance and marks unhealthy keys automatically
- **Easy Setup**: Simply add additional keys to `GEMINI_API_KEYS` in your `.env` file

**Benefits:**
- 🚀 Increased reliability and uptime
- ⚡ Better performance through load distribution
- 🛡️ Automatic recovery from API failures
- 📊 Built-in monitoring and statistics

### Large File Download Setup 📦

For downloading PDFs larger than 20MB, you need to set up a Pyrogram user account:

1. **Get API Credentials**:
   - Go to https://my.telegram.org/apps
   - Log in with your phone number
   - Create an application (if needed)
   - Copy your `api_id` (integer) and `api_hash` (string)

2. **Choose Authentication Method**:

   **Option A: Session String (Recommended for CI/CD, GitHub Actions)**
   
   For automated deployments, GitHub Actions, or CI/CD pipelines, use a session string:
   
   **Method 1: Using the helper script (Recommended)**
   
   ```bash
   python generate_session_string.py
   ```
   
   The script will guide you through the process and output the session string.
   
   **Method 2: Manual generation**
   
   ```python
   # Generate session string (run once locally)
   from pyrogram import Client
   
   api_id = YOUR_API_ID  # Your API ID from my.telegram.org
   api_hash = "YOUR_API_HASH"  # Your API hash
   
   # This will prompt for phone number and code once
   app = Client("temp_session", api_id=api_id, api_hash=api_hash)
   app.start()
   session_string = app.export_session_string()
   print(f"Session String: {session_string}")
   app.stop()
   ```
   
   Then add to `.env`:
   ```env
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_SESSION_STRING=your_generated_session_string
   ```
   
   **Option B: Interactive Authentication (Local Development)**
   
   For local development, you can use interactive authentication:
   
   ```env
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   # Leave TELEGRAM_SESSION_STRING empty
   ```
   
   On first run, the bot will prompt for your phone number and authentication code. A session file (`tss_bot_pyrogram_user.session`) will be created automatically.

3. **For GitHub Actions / CI/CD**:
   - **You MUST use session string** (Option A) to avoid interactive prompts
   - Generate the session string locally using the helper script
   - Add `TELEGRAM_SESSION_STRING` as a GitHub Secret (Settings → Secrets and variables → Actions)
   - Also add `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` as secrets
   - In your GitHub Actions workflow, reference them:
     ```yaml
     env:
       TELEGRAM_API_ID: ${{ secrets.TELEGRAM_API_ID }}
       TELEGRAM_API_HASH: ${{ secrets.TELEGRAM_API_HASH }}
       TELEGRAM_SESSION_STRING: ${{ secrets.TELEGRAM_SESSION_STRING }}
     ```
   - The session string is equivalent to your account password - keep it secure!

**Note**: 
- Without user account credentials, the bot falls back to bot token (20MB limit)
- Session strings and session files contain authentication data - keep them secure and never commit them to git
- If you see a warning about "TgCrypto is missing", install `pycryptodome` for better performance: `pip install pycryptodome` (optional but recommended)
- Make sure the session string is generated with the same `api_id` and `api_hash` you're using in your `.env` file

## Bot Commands 🤖

- `/start` - Welcome message and quick start guide
- `/help` - Comprehensive documentation and usage guide
- `/settings` - Open the settings menu to configure general options
- `/gen <prompt>` - Generate custom quizzes with your instructions (e.g., `/gen সত্যু মিথ্যা প্রশ্ন বানিয়ে দাও`)
  - Reply to an image with `/gen prompt` OR send an image first, then use `/gen prompt`
  - Works with Bengali and English prompts
- `/db` - Manage MongoDB-backed settings (marker/link, explanations toggle, channels, groups, authorized users)
- `/debug` - Get technical information like chat and topic IDs for configuration
- `/logs` or `/status` - View detailed system logs, metrics, uptime, network ping, speed, and comprehensive status
- `/config` - View detailed system configuration
- `/start_poll_collection` - Enable poll collection mode

### Live Quiz Mode

- Create a quiz interactively with `/newquiz` (title, description, timers).
- Forward Telegram quiz polls to add questions, then send `done`.
- Toggle shuffling and negative marking (−0.25) before saving.
- The bot returns a deep link: `/start quiz_<id>` (plus buttons to preview, copy link, and start in a group). Share it anywhere; Telegram shows quiz title and description.
- Learners see a “Get ready” card with an `I am ready!` button and a countdown (3 s in private chats, 10 s in groups).
- During a live run, each question is sent as a non-anonymous quiz poll with per-question timer and numbered options (1,2,3,4).
- Scoring: correct +1, wrong −0.25 (if enabled), skipped 0. A leaderboard is shown at the end.
- After the quiz, a share button lets you restart it in another group instantly.
- Env: set `BOT_USERNAME` for proper deep links.

## Usage Guide 📝

1. **Configure the bot**:
   - Use `/settings` to set your preferred mode and topic
   - Toggle explanations on/off based on your needs

2. **Setting up topics**:
   - **By Name**: When prompted, enter a topic name - the bot will find or create it
   - **By ID**: Enter a numeric topic ID directly to use an existing topic
   - Use `/debug` to get IDs of existing topics in your group

3. **Send images containing questions**:
   - **Single Image**: Send one image at a time for individual processing
   - **Multiple Images**: Select multiple images and send them together as a group
   - Each question should have exactly 4 options (A, B, C, D format)
   - Images with answer keys at the bottom will have answers automatically detected
   - Images should be clear and well-lit for optimal text extraction

4. **Processing options**:
   - After image processing completes, use the "Send All Quizzes" button to automatically send all questions
   - Or review each question individually:
     - The bot will show detected answers as "Selected Answer X: [answer text]"
     - If no answer was detected, the AI will suggest one (marked with 💡)
     - You can select a different answer if needed
     - Optionally edit the question or options
     - Preview the Bengali explanation
     - Confirm to send as an interactive quiz

5. **After quiz creation**:
   - Use the Copy button to get formatted text for sharing
   - View the full Bengali explanation
   - Share the quiz with students/users

6. **PDF workflow**:
   - Send a PDF document; the bot replies with total pages and asks for a page range (e.g., `1-10`)
   - If the PDF is too large for Telegram document download, send a direct link to the PDF (http/https)
   - The bot converts each selected page to an image and processes them like photos

7. **CSV/JSON import/export**:
   - CSV/JSON imports now do NOT auto-send. After import, you get action buttons:
     - "Send All Quizzes", "PDF F1", "PDF F2", "CSV", "JSON"
   - CSV export format: `question, option1, option2, option3, option4, option5, answer, explination`
   - Notes:
     - `answer` is 1-based (1..5)
     - `option5` is optional
     - `QUIZ_MARKER` is removed from exported questions
     - Any `QUIZ_EXPLANATION_LINK` and URLs are stripped from the `explination` column

8. **Custom Prompt Mode (`/gen` command)**:
   - Send an image or reply to an image
   - Use `/gen` followed by your instructions in Bengali or English
   - Examples:
     - `/gen সত্যু মিথ্যা প্রশ্ন বানিয়ে দাও, ২০টা প্রশ্ন বানিয়ে দাও`
     - `/gen কঠিন প্রশ্ন তৈরি করো`
     - `/gen Create 10 easy questions`
   - The bot generates questions based on your custom prompt
   - Works with textbook images and regular quiz images

9. **Large PDF Processing**:
   - For PDFs >20MB, the bot automatically uses Pyrogram user account (if configured)
   - Supports files up to 2GB when using user account credentials
   - For very large files, you can also send a direct HTTP/HTTPS link
   - No manual intervention needed - automatic detection and handling

## MongoDB-Backed Settings 🗄️

The bot uses MongoDB for persistent, per-user settings management:

### Database Configuration
- **Per-User Settings**: Each user can have their own configuration
- **Global Defaults**: Fallback to global settings if user-specific not set
- **Environment Fallback**: Falls back to `.env` values if DB is empty
- **Auto-Seeding**: On first run, `.env` values are automatically seeded to MongoDB

### Managing Settings via `/db`

Use `/db` command to view and modify settings stored in MongoDB:

- **Quiz Marker**: View/edit the prefix marker for quizzes
- **Explanation Link**: View/edit the attribution link for explanations
- **Explanations**: Toggle ON/OFF for answer explanations
- **Channels**: 
  - List all channels
  - Add new channel (with title, username, chat_id)
  - Remove channel
  - Set default channel
- **Groups**: 
  - List all groups
  - Add new group (with title, username, chat_id)
  - Remove group
  - Set default group
- **Authorized Users**: 
  - List all authorized users
  - Add new authorized user
  - Remove authorized user

### Per-User Configuration
- Each user can set their own default channel and group
- Settings are stored per-user in MongoDB
- When sending quizzes, user-specific defaults are used (if set), otherwise global defaults, otherwise `.env` values

8. **PDF export**:
   - After generating quizzes, click "Export PDF (Format 1)", "Export PDF (Format 2)", or "Export PDF (Format 3)"
   - Format 1: Practice Sheet with answers and explanations inline (2-column layout)
   - Format 2: Questions in 2 columns, then a separate answer table with explanations
   - Format 3: Exam Style - Questions in 2 columns with answer key table at bottom (no explanations)
   - PDFs are A4-sized with proper Bengali font rendering and MathJax support
   - Color scheme: Maroon (#800000) accent colors
   - Also available from `/settings` if you have quiz data in your current batch

10. **Poll collection to CSV**:
    - Enable/disable from `/settings` or use `/start_poll_collection`
    - Forward or send quiz polls; the bot counts them (status message updates automatically)
    - Send `done` to receive a merged CSV export
    - Status message is edited instead of creating new messages (cleaner interface)

11. **Progress Tracking**:
    - Detailed progress messages during quiz generation
    - Step-by-step status updates for each processing stage
    - Clear error messages with helpful tips
    - Real-time feedback for image/PDF processing

## Bengali Textbook Mode 📚

- **Activation**: Enable via `/settings`
- **Input**: Send clear images or PDF pages of textbook content (biology, physics, chemistry, manobik gunaboli)
- **Output**: Multiple professionally crafted Bengali MCQs per image with explanations
- **Format**: Each question includes:
  - Question text in Bengali
  - 4 answer options (A, B, C, D) in Bengali
  - Pre-selected correct answer
  - Concise Bengali explanation (165 characters)
- **Features**:
  - Preserves mathematical and chemical expressions
  - Handles complex diagrams and equations
  - Supports Bengali numerals and special characters
- **Editing**: Full support for editing questions and options
- **Perfect for**: Teachers creating assessment materials in Bengali
- **AI Engine**: Powered by Google Gemini 2.5 Flash for high-quality Bengali content

## MBBS Mode 🏥

- **Activation**: Enable via `/settings`
- **Input**: Send clear images or PDF pages from medical textbooks
- **Output**: Multiple medical MCQs with clinical scenarios and explanations
- **Format**: Each question includes:
  - Question text (may include clinical vignettes)
  - 4 answer options (A, B, C, D)
  - Pre-selected correct answer
  - Concise medical explanation (165 characters)
- **Subject Coverage**: All MBBS subjects including:
  - Anatomy, Physiology, Biochemistry
  - Pathology, Pharmacology, Microbiology
  - Medicine, Surgery, Obstetrics & Gynecology
  - Pediatrics, Ophthalmology, ENT, Orthopedics
  - Psychiatry, Dermatology, Radiology, Anesthesiology
  - Emergency Medicine, Forensic Medicine, Community Medicine
- **Question Types**:
  - Clinical scenario/vignette-based questions
  - Basic science and recall questions
  - USMLE/PLAB-style questions
- **Perfect for**: Medical students preparing for exams
- **AI Engine**: Powered by Google Gemini 2.5 Flash with specialized medical prompts

## Multi-Image Processing System 📷

- **Automatic Detection**: Bot automatically detects when multiple images are sent together
- **Seamless Handling**: All images in a group are processed sequentially
- **Progress Tracking**: Shows detailed progress for each image being processed
- **Unified Results**: Combines all questions from all images into a single batch
- **Error Resilience**: Continues processing even if some images fail
- **Combined Interface**: Shows a single interface for all extracted questions
- **Optimal for Exams**: Perfect for processing multi-page exam papers

## Topic Management System 📂

- **Topic Creation**: Enter a name to create a new forum topic
- **Topic Selection**: Enter a name to use an existing topic
- **Direct ID Input**: Enter a numeric topic ID to use a specific topic directly
- **Similar Topic Detection**: Automatically suggests similar topics to avoid duplicates
- **Flexible Navigation**: Change topics at any time through the settings menu

## Answer Detection System 🔍

- **Automatic Detection**: Scans images for answer keys, typically at the bottom of exam papers
- **Multiple Formats Supported**:
  - Answer grids (e.g., "1 2 3 4 5" with "B B C B D" below)
  - Individual answer notations below each question
- **Fallback System**: Uses AI to suggest answers when automatic detection isn't possible
- **Clear Answer Display**: Shows "Selected Answer X: [answer text]" format for clarity

## Explanation System 📚

- Generates concise Bengali language explanations (165 character limit)
- Explanations focus on why the correct answer is correct
- Automatically cleans out metadata text and character count references
- Added to the quiz's "lightbulb" button for educational feedback
- Preview explanations before confirming the answer
- Professional attribution with clickable t.me link automatically added

## Content Requirements 📋

- **Image Quality**: Clear, readable text with good lighting
- **Question Format**: Standard multiple-choice format with 4 options
- **Answer Key Format**: For optimal detection, include an answer key at the bottom of the page
- **Character Limits**:
  - Questions: 280 characters maximum
  - Options: 95 characters per option
  - Explanations: 165 characters maximum for quiz display

## Error Handling ⚠️

The bot includes comprehensive error handling for:
- Image processing issues
- Text extraction problems
- Large PDFs sent as documents (Telegram limit) — use a direct link instead
- Message length limitations (with automatic truncation)
- Rate limiting and retry mechanisms
- Invalid chat/topic IDs
- Malformed questions

## Concurrency and Multi-user Support ⚙️

- The bot supports concurrent processing for multiple users.
- Configure the maximum parallel users with `MAX_CONCURRENT_USERS` (default `100`).
- Per-user session control prevents overlapping work for the same user while allowing others to proceed.
- **Performance Optimizations**:
  - Configurable thread pool workers (`THREAD_POOL_WORKERS`, default `20`)
  - Configurable connection pool size (`CONNECTION_POOL_SIZE`, default `100`)
  - Configurable parallel PDF page processing (`MAX_PARALLEL_PAGES`, default `4`)
  - Optimized timeouts for better concurrent request handling
  - Async HTTP client for non-blocking file downloads

## Contributing 🤝

Feel free to open issues or submit pull requests for improvements. The main areas for potential enhancement include:
- Supporting additional languages for explanations
- Improving answer key detection accuracy
- Adding more quiz format options
- Enhancing AI prediction accuracy

## License 📄

This project is available for educational and personal use. Please respect the terms of service of all APIs used in this project.

---

Made with ❤️ by @notenderdreams & @XenonTheInertG