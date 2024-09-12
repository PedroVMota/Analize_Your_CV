import os
import json
import hashlib  # Importing hashlib for the hash function
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import openai
import PyPDF2
from docx import Document
from dotenv import load_dotenv
import utils.Skills 
# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Path to store the cached responses
CACHE_DIR = os.path.join(os.getcwd(), "cached_responses")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Function to generate a stable hash of the CV content using SHA-256
def generate_hash(cvText):
    return hashlib.sha256(cvText.encode('utf-8')).hexdigest()

# Function to handle AI response caching and analysis
def aiResultion(cvText, cache_file_path):
    client = openai.Client()

    # Call OpenAI API if no cached result exists
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that analyzes CVs for IT and tech-related jobs. Your task is to extract the most relevant keywords and determine the most compatible job field and skills for each CV."
            },
            {
                "role": "user",
                "content": f"From the following CV, extract the most relevant keywords related to IT and tech jobs. You need to:\n"
                    f"1. Identify and extract key technical skills from the CV.\n"
                    f"2. Identify the major field(s) the CV is related to by matching them with common tech job categories.\n"
                    f"3. Provide a detailed output in JSON format, estimating the relevance (in percentage) of the CV to each potential job field. Do not forget to add only 5 fields that you think the CV is related to ( The top 5 fields )."
                    f"4. Provide any additional information that you think is relevant about the resolution of the solution. You must explain your conclusion under the `extra_info` key.\n"
                    f"5. The final output **must** be a valid JSON format, as follows:\n"
                    f"{{\"Software Development\": 80, \"Data Science\": 20, \"extra_info\": \"The current CV is more related to Software Development because it contains a lot of keywords related to programming languages and frameworks.\"}}\n"
                    f"6. **You must ONLY output the valid JSON response.** Do not include any other text or comments in the output.\n"
                    f"7. If your output is not valid JSON or includes extra text, it will be considered incorrect.\n"
                    f"8. The fields that you must use you can create your own fields by the way {[eachOne for eachOne in utils.Skills.tech_jobs]}, make sure you give only the top 5 fields that you think the CV is related to."
                    f"CV Content: {cvText}"
            }
        ],
        max_tokens=2000
    )

    jsonData = response.choices[0].message.content

    # Save the AI response to the cache file
    with open(cache_file_path, "w") as cache_file:
        cache_file.write(jsonData)

    return jsonData

# CV analysis view
@require_http_methods(["POST"])
def analise_cv(request):
    try:
        if 'cv_file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        cvFile = request.FILES['cv_file']
        cvFileExtension = cvFile.name.split('.')[-1].lower()

        if cvFileExtension not in ['pdf', 'doc', 'docx']:
            return JsonResponse({'error': 'Invalid file format'}, status=400)

        # Extract text from the file
        cvText = ''
        if cvFileExtension == 'pdf':
            pdfReader = PyPDF2.PdfReader(cvFile)
            for page in pdfReader.pages:
                cvText += page.extract_text()
        elif cvFileExtension in ['doc', 'docx']:
            doc = Document(cvFile)
            for para in doc.paragraphs:
                cvText += para.text
        else:
            return JsonResponse({'error': 'Unsupported file format'}, status=400)

        # Generate a unique file name based on the CV content using SHA-256
        cache_file_name = f"{generate_hash(cvText)}.json"
        cache_file_path = os.path.join(CACHE_DIR, cache_file_name)

        # Check if the cache file exists
        if os.path.exists(cache_file_path):
            # If cached response exists, read the cached result
            with open(cache_file_path, "r") as cache_file:
                cached_response = cache_file.read()
            print("Using cached response")
            jsonData = json.loads(cached_response)
        else:
            # If no cache exists, call the AI and save the result to a file
            ai_response = aiResultion(cvText, cache_file_path)
            try:
                jsonData = json.loads(ai_response)
                print("AI response received")
            except json.JSONDecodeError:
                print("Failed to parse AI response")
                return JsonResponse({'error': 'Failed to parse AI response'}, status=500)

        # Ensure the extra_info field is present
        if not isinstance(jsonData, dict) or "extra_info" not in jsonData:
            jsonData["extra_info"] = "No additional information provided by the AI."

        return JsonResponse({
            "results": jsonData,
            "extra_info": jsonData.get("extra_info", "")
        })
    
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

# Index view
def index(request):
    return render(request, 'index.html')