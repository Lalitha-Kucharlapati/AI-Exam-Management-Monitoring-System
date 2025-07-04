# genai_utils.py
import requests
from config import HUGGINGFACE_API_URL, HUGGINGFACE_MODEL, HUGGINGFACE_HEADERS
import os
from dotenv import load_dotenv
load_dotenv()

def generate_mcqs(topic):
    import requests
    import json

    token = os.getenv("HUGGINGFACE_TOKEN")
    url = "https://router.huggingface.co/novita/v3/openai/chat/completions"
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

    data = {
    "model": "deepseek/deepseek-r1-turbo",
    "messages": [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that generates MCQs for exams.\n"
                "Generate exactly 20 multiple-choice questions (MCQs) with one correct answer each.\n"
                "Use the following format strictly:\n\n"
                "Q1: <question text>\n"
                "A. <option A>\n"
                "B. <option B>\n"
                "C. <option C>\n"
                "D. <option D>\n"
                "Answer: <correct option letter>\n\n"
                "Repeat this format for Q2 to Q20.\n"
                "Do not include explanations."
            )
        },
        {
            "role": "user",
            "content": f"Topic: {topic}"
        }
    ]
}

    res = requests.post(url, headers=headers, data=json.dumps(data))

    # Print the full response for inspection
    try:
        response_json = res.json()
        print("DEBUG - FULL HF API RESPONSE:")
        print(json.dumps(response_json, indent=2))
    except Exception as e:
        print("Error decoding response JSON:", e)
        print("Raw text:", res.text)
        return "Error: Invalid response from Hugging Face API"

    # Safe fallback if 'choices' key is missing
    try:
        return response_json['choices'][0]['message']['content']
    except KeyError:
        return response_json.get('text', 'Error: No MCQs generated')



def evaluate_subjective(answer, question):
    prompt = f"Evaluate the following answer to the question:\nQ: {question}\nA: {answer}\nGive a score out of 20."
    return ask_model(prompt)

def ask_model(prompt):
    data = {
        "model": HUGGINGFACE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    res = requests.post(HUGGINGFACE_API_URL, headers=HUGGINGFACE_HEADERS, json=data)
    res.raise_for_status()
    return res.json()['choices'][0]['message']['content']
