# 🚀 Auto LinkedIn Job Applier

This project automatically finds and applies to LinkedIn jobs based on your configured preferences.  
It uses Selenium WebDriver to simulate human-like interaction and OpenAI to intelligently decide which jobs to apply for (optional).

---

## ✨ Features

- Automatically search for jobs based on keywords and location.
- Apply filters like "Easy Apply" only.
- Smart job relevance checking using AI model (optional).
- Auto-fill common application questions (salary, visa sponsorship, etc).
- Automatically upload your resume.
- Skip unwanted jobs based on blocked keywords.
- Safe retries and error handling to avoid detection.

---

## ⚙️ Requirements

- Python 3.8 or higher
- Google Chrome browser
- ChromeDriver installed
- Python libraries:
  - selenium
  - pyautogui
  - openai (optional, for AI relevance check)

---

## 🛠️ Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/iddeepak/auto_apply_jobs.git
   cd auto-job-applier
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your personal information:
   - Update `config/personals.py` (your name, phone, salary, etc.)
   - Update `config/secrets.py` (LinkedIn username, password, OpenAI API key if needed)

4. Place your resume:
   - Add your resume inside the `resumes/` folder.
   - Update `default_resume_path` if needed in your configuration.

5. Run the application:
   ```bash
   python main.py
   ```

---

## 🧠 How AI Matching Works (Optional)

If `use_AI` is set to `True`:
- The bot checks job descriptions using OpenAI API.
- It automatically skips jobs that are not relevant to your skills.
- Saves your time and increases success rate.

If you don't want AI matching, simply set `use_AI = False`.

---

## ⚠️ Notes

- Only Easy Apply jobs are supported.
- Avoid running the bot for too many continuous hours.
- Regularly monitor LinkedIn to avoid any account issues.
- Always keep your resume updated.

---

## ❤️ Credits

Developed with love and coffee.  
Feel free to modify and improve it.

---

# 🚀 Happy Job Applying!
