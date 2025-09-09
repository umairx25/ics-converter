import os
from dotenv import load_dotenv
from google import genai
import pymupdf

dotenv = load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
client = genai.Client(api_key=GEMINI_API_KEY)

def parse_pdf(file):
    """
    Given a dataset comprising of pdf files, extract text from each file and return
    the extracted string
    """
    res = {}

    with pymupdf.open(stream= file.read(), filetype="pdf") as doc:
        res = chr(12).join([page.get_text() for page in doc])

    return res

def generate_content(model, query):
    """
    Return the response returned by the Gemini API given a model and query
    """
    response = client.models.generate_content(model=model, contents=query, config={
        "response_mime_type": "application/json"  # <- the key line
    },)
    return response.text

def create_events(txt: str):
    """
    Given some input text from the user, return a structured json with each key-
    value pair corresponding to an event
    """
    json_format = {
    "name": "CS101 Lab",
    "begin": "2025-09-12T14:00",
    "end": "2025-09-12T16:00",
    "duration": "null",
    "uid": "cs101-lab-001",
    "description": "Odd weeks only",
    "created": "null",
    "last_modified": "null",
    "location": "WB 105",
    "url": "null",
    "transparent": "null",
    "alarms": "null",
    "attendees": "null",
    "status": "CONFIRMED",
    "organizer": "null",
    "geo": "null",
    "classification": "null",
    "recurrence": {
        "type": "ODD_WEEKS",
        "days": ["FR"],
        "interval": 2,
        "until": "2025-12-15"
    },
    "exceptions": {
        "exdates": []
    }
    }

    prompt = f"You are given the following text: {txt}.\
    Your task:\
    - Extract all events and output a **single valid JSON object**.\
    - The JSON must exactly match this structure: {json_format}\
    Put all this under the 'events' key.\
    Under the timezone key, put in the timezone most likely associated with the given text, defualt to EST\
    Under the 'filename' key, put in an appropraite filename based on the text i.e schedule, timetable, meetings etc.\
    Rules:\
    - **Return ONLY the JSON** — no extra text, no backticks, no explanations.\
    - If information is missing, i.e there is 'null', leave the field out entirely.\
    "

    res = generate_content(MODEL, prompt)

    return res
