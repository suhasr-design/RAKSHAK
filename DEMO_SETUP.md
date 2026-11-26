# Running the Rakshak demo (for teammates)

Do this **the day before** judging, so the first-time setup is already done.

## You need
- A Windows laptop with internet.
- **Python 3.11 or newer**: https://www.python.org/downloads/ (during install, tick **"Add python.exe to PATH"**).

You do **not** need Node.js or Git.

## Steps
1. Open https://github.com/suhasr-design/RAKSHAK, click the green **Code** button, then **Download ZIP**.
2. Extract the ZIP to a short path, e.g. `C:\RAKSHAK`. Don't run it from inside the ZIP, and preferably not from a OneDrive folder, which makes it slow.
3. Double-click **`run_demo.bat`**.
   - First time: it installs everything (2–5 minutes).
   - Then the demo opens at **http://127.0.0.1:8000**. If the browser doesn't open, type that address in yourself.
   - Keep the black window open during the demo. Close it to stop.
   - If Windows shows "Windows protected your PC", click **More info → Run anyway**.
4. In the page, set **LLM** to **"Offline: worst-case gullible LLM"**. It's the most reliable option for judging: no internet or API key needed, and the same result every time.

## Optional: live Groq model
Create a file named `.env` next to `run_demo.bat` containing:
```
GROQ_API_KEY=gsk_...
```
Get the key from the team privately. **Never commit it or paste it in chat.** Then choose **Groq (live)** in the LLM menu. The free tier can rate-limit you, so keep the offline mode as your fallback.

## During the judging round
- Click **Run** on the left panel (plain assistant → COMPROMISED), then **Run** on the right panel → approve the permission screen → SAFE.
- **Replay speed** and **⏸ Pause / ⏭ Step** let you slow down and talk through each step.
- Backup if anything fails: play the demo section of the pitch video, starting around 1:50.

## Troubleshooting
| Problem | Fix |
|---|---|
| "Python 3.11 or newer was not found" | Install Python (link above) with "Add to PATH" ticked, then run again |
| Setup failed midway | Check internet, then run `run_demo.bat` again (it starts fresh) |
| Page says "Cannot reach the demo backend" | The black window was closed; double-click `run_demo.bat` again |
| Port 8000 already in use | Close any other running copy of the demo, or restart the laptop |
