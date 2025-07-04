# Updated app.py with Google Sheet-based question paper generation and delivery
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template, request, redirect, url_for, session
from genai_utils import generate_mcqs, evaluate_subjective
from gsheet_utils import save_result, get_all_results, create_question_sheet, get_latest_questions, delete_all_question_sheets
import threading
import invigilation_ai
import audio_monitor

from shared_flags import status_flags, monitoring_flags


face_storage = {} 

# Google Sheets Setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

mentor_sheet = client.open("Mentor_Users").sheet1
student_sheet = client.open("Student_Users").sheet1


app = Flask(__name__)
app.secret_key = '12f2e14994d12d2158b044227ff441dca1dea0368ba9c288'  # Required for sessions


@app.route('/')
def home():
    return render_template('index.html')

@app.route("/instructor_login_page")
def mentor_login_page():
    return render_template("instructor_login.html")

@app.route("/student_login_page")
def student_login_page():
    return render_template("student_login.html")

@app.route("/instructor_signup_page")
def mentor_signup_page():
    return render_template("instructor_signup.html")

@app.route("/student_signup_page")
def student_signup_page():
    return render_template("student_signup.html")

@app.route("/instructor_login", methods=["POST"])
def instructor_login():
    email = request.form["email"]
    password = request.form["password"]
    records = mentor_sheet.get_all_records()
    for row in records:
        if row["email"] == email and row["password"] == password:
            return redirect("/instructor")
    return "<h3>Incorrect credentials. <a href='/'>Back to Home</a></h3>"

@app.route("/instructor_signup", methods=["POST"])
def instructor_signup():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    mentor_sheet.append_row([name, email, password])
    return redirect("/")

@app.route("/student_login", methods=["POST"])
def student_login():
    email = request.form["email"]
    password = request.form["password"]
    records = student_sheet.get_all_records()
    for row in records:
        if row["email"] == email and row["password"] == password:
            session['student_name'] = row["name"]
            session['student_email'] = row["email"]
            session['student_password'] = password
            return redirect("/exam")
    return "<h3>Incorrect credentials. <a href='/'>Back to Home</a></h3>"

@app.route("/student_signup", methods=["POST"])
def student_signup():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    student_sheet.append_row([name, email, password])
    return redirect("/")


@app.route('/instructor', methods=['GET', 'POST'])
def instructor():
    questions = []
    sheet_url = ""
    if request.method == 'POST':
        topic = request.form['topic']
        result = generate_mcqs(topic)

        # Clean up MCQs
        lines = result.strip().splitlines()
        clean_lines = [line.strip() for line in lines if line.strip() and not line.lower().startswith("<") and len(line.strip()) < 200]
        questions = clean_lines

        # Create new Google Sheet and save questions
        sheet_url = create_question_sheet(topic, questions)

    return render_template('instructor.html', questions=questions, sheet_url=sheet_url)

@app.route('/view_results')
def view_results():
    results = get_all_results()
    return render_template('results.html', results=results)

@app.route('/start_exam', methods=['GET', 'POST'])
def start_exam():
    if 'student_name' not in session or 'student_email' not in session:
        return redirect('/student_login_page')

    parsed_questions = get_latest_questions()
    if not parsed_questions:
        return "No exam available. Instructor has not uploaded any questions."

    name = session['student_name']
    email = session['student_email']

    if request.method == 'POST':
        face_b64 = request.form.get("face_image")
        print("DEBUG - face_b64 received:", face_b64[:50] if face_b64 else "None")

        if not face_b64:
            return "Error: Face image not received. Please allow camera access and try again."

        # ✅ Store in global dict instead of session
        face_storage[email] = face_b64

        # ✅ Start monitoring
        invigilation_ai.monitoring_flags[name] = True
        threading.Thread(target=invigilation_ai.start_camera_monitoring, args=(name, face_b64), daemon=True).start()
        print("✅ Face monitoring thread started.")

        threading.Thread(target=audio_monitor.start_audio_monitoring, args=(name,), daemon=True).start()
        print("✅ Voice monitoring thread started.")

        return render_template('exam.html', questions=parsed_questions)

    return render_template('exam_intro.html')


@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if 'student_name' not in session or 'student_email' not in session:
        return redirect('/student_login_page')

    name = session['student_name']
    email = session['student_email']

    # ✅ Fetch face from memory
    face_b64 = face_storage.get(email, '')
    print("DEBUG - face_b64 being saved:", face_b64[:50] if face_b64 else "None")

    # ✅ Fetch questions and answers
    questions = get_latest_questions()
    correct_answers = []
    student_answers = []

    # ✅ Open question sheet
    exam_sheet = client.open("Latest_Exam").sheet1
    rows = exam_sheet.get_all_values()

    print("DEBUG: Loaded rows from sheet:")
    for r in rows:
        print(r)

    for i, row in enumerate(rows[1:]):  # Skip header
        if len(row) > 5:
            correct = row[5].replace("Answer:", "").strip().lower()
        else:
            correct = ""  # or log an error / skip this row

        correct_answers.append(correct)

        student_input = request.form.get(f'q{i}')
        student_input = student_input.strip().lower() if student_input else ''
        student_answers.append(student_input)

    print("Student Answers:", student_answers)
    print("Correct Answers:", correct_answers)

    # ✅ Calculate score
    score = sum(1 for s, c in zip(student_answers, correct_answers) if s == c)
    feedback = f"{score}/{len(correct_answers)} correct"

    # ✅ Stop monitoring
    invigilation_ai.monitoring_flags[name] = False
    print(f"🛑 Monitoring stopped for {name}")

    # ✅ Save to Google Sheet
    save_result(name, email, student_answers, score, feedback, face_b64)

    return render_template("results.html", score=score)

@app.route('/check_status')
def check_status():
    name = session.get('student_name')
    status = status_flags.get(name, 'OK')
    print(f"📡 Status check for {name}: {status}")
    return status


@app.route('/exam', methods=['GET'])
def exam_intro():
    if 'student_name' not in session:
        return redirect('/student_login_page')
    return render_template('exam_intro.html')

@app.route('/terminated')
def terminated():
    return render_template("terminated.html")

if __name__ == '__main__':
    app.run(debug=True)
