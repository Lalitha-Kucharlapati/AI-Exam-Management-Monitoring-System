import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import CREDENTIALS_FILE

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)

RESULT_SHEET_NAME = "Exam_Results"
question_prefix = "Exam_Questions_"

# Result sheet
sheet = client.open(RESULT_SHEET_NAME).sheet1

def save_result(name, email, answers, score, feedback, face_b64):
    headers = ["Name", "Email", "face_b64"] + [f"Q{i+1}" for i in range(len(answers))] + ["Score", "feedback"]
    
    sheet = client.open("Exam_Results").sheet1  # ✅ Define sheet first

    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(headers)  # ✅ Insert headers if sheet is empty

    print("DEBUG - face_b64 being saved:", face_b64[:50])

    row = [name, email, face_b64] + answers + [score] + [feedback]
    sheet.append_row(row)

def get_all_results():
    records = sheet.get_all_values()
    if not records or len(records) < 2:
        return []
    headers = records[0]
    return [dict(zip(headers, row)) for row in records[1:]]

def create_question_sheet(topic, questions):
    sheet = client.open("Latest_Exam").sheet1
    sheet.clear()
    sheet.append_row(['Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Answer'])

    grouped = []
    current_q = ""
    options = []
    correct = ""

    for line in questions:
        line = line.strip()
        if line.lower().startswith('q'):
            if current_q and options and correct:
                grouped.append((current_q, options[:4], correct))
            current_q = line
            options = []
            correct = ""
        elif line[:2] in ['A.', 'B.', 'C.', 'D.']:
            options.append(line)
        elif line.lower().startswith("answer:"):
            correct = line.split(":", 1)[-1].strip().upper()  # Extract just the letter

    # Add last group
    if current_q and options and correct:
        grouped.append((current_q, options[:4], correct))

    for q, opts, ans in grouped:
        opts_clean = [opt.strip() for opt in opts]
        while len(opts_clean) < 4:
            opts_clean.append("")
        sheet.append_row([q] + opts_clean + [ans])

    print("DEBUG - Questions written to sheet:")
    for q, opts, ans in grouped:
        print(q, opts, ans)

    return "https://docs.google.com/spreadsheets/d/1rkBJPZQoAYguFNqBv6AI9_W9k8u-tL2J_W1fQwctZ7U"



def get_latest_questions():
    try:
        sheet = client.open("Latest_Exam").sheet1
        data = sheet.get_all_values()
        parsed = []

        for row in data[1:]:
            if len(row) >= 5:
                parsed.append({
                    "question": row[0],
                    "options": row[1:5]
                })
        return parsed
    except:
        return []


def delete_all_question_sheets():
    files = client.list_spreadsheet_files()
    for f in files:
        if f['name'].startswith(question_prefix):
            client.del_spreadsheet(f['id'])
