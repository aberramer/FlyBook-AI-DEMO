from flask import Flask, request, jsonify
from flights.google_flight_scraper import get_flight_url, scrape_flights
from flights.hotels import BrightDataAPI
import requests
import asyncio
import uuid
import threading
from enum import Enum
from collections import defaultdict
from waitress import serve
from flask_cors import CORS # Yeni ekle: CORS hatalarını önlemek için
import os # Yeni ekle: .env dosyasını okumak için
from dotenv import load_dotenv # Yeni ekle: .env dosyasını okumak için
from langchain_openai import ChatOpenAI # Yeni ekle: OpenAI LLM için
from langchain_core.prompts import ChatPromptTemplate # Yeni ekle: Prompt oluşturmak için
from langchain_core.output_parsers import JsonOutputParser # Yeni ekle: JSON çıktıyı parse etmek için
from langchain_core.runnables import RunnablePassthrough # Yeni ekle: LangChain zinciri için
from langchain_core.pydantic_v1 import BaseModel, Field # Yeni ekle: Pydantic modelleri için

# .env dosyasındaki API anahtarını yükle
load_dotenv()

app = Flask(__name__)
CORS(app) # Tüm kaynaklardan gelen isteklere izin ver (geliştirme için)

# In-memory storage for task results (Orijinal haliyle kalıyor)
task_results = defaultdict(dict)
# Lock for thread-safe operations on task_results (Orijinal haliyle kalıyor)
task_lock = threading.Lock()

class TaskStatus(Enum): # Orijinal haliyle kalıyor
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

def run_async(coro): # Orijinal haliyle kalıyor
    """Helper function to run async code"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def update_task_status(task_id, status, data=None, error=None): # Orijinal haliyle kalıyor
    """Thread-safe update of task status"""
    with task_lock:
        if data is not None:
            task_results[task_id].update({
                'status': status,
                'data': data
            })
        elif error is not None:
            task_results[task_id].update({
                'status': status,
                'error': error
            })
        else:
            task_results[task_id]['status'] = status

# Orijinal flight ve hotel arama işlemleri (Şimdilik dokunmuyoruz, ancak frontend bu API'leri çağırmayacak)
def process_flight_search(task_id, origin, destination, start_date, end_date, preferences):
    # Bu fonksiyon orijinal projeye ait. Demoda kullanmayacağız.
    print(f"Skipping original flight search for task {task_id}")
    update_task_status(task_id, TaskStatus.COMPLETED.value, data="Flight search simulated/skipped in demo.")

def process_hotel_search(task_id, location, check_in, check_out, occupancy, currency):
    # Bu fonksiyon orijinal projeye ait. Demoda kullanmayacağız.
    print(f"Skipping original hotel search for task {task_id}")
    update_task_status(task_id, TaskStatus.COMPLETED.value, data="Hotel search simulated/skipped in demo.")

# Orijinal /search_flights, /search_hotels, /task_status endpointleri (Değişmiyor)
# Frontend'i bu endpointleri çağırmayacak şekilde güncelleyeceğiz
@app.route('/search_flights', methods=['POST'])
def search_flights():
    data = request.get_json()
    task_id = str(uuid.uuid4())
    with task_lock:
        task_results[task_id] = {'status': TaskStatus.PENDING.value}
    # Demoda bu kısmı atlıyoruz, gerçek arama yapmıyoruz
    # thread = threading.Thread(target=process_flight_search, args=(task_id, data.get('origin'), data.get('destination'), data.get('start_date'), data.get('end_date'), data.get('preferences')), daemon=True)
    # thread.start()
    print(f"Simulating flight search task {task_id}")
    update_task_status(task_id, TaskStatus.COMPLETED.value, data="Simulated flight search data.")
    return jsonify({'task_id': task_id, 'status': TaskStatus.PENDING.value})

@app.route('/search_hotels', methods=['POST'])
def search_hotels():
    data = request.get_json()
    task_id = str(uuid.uuid4())
    with task_lock:
        task_results[task_id] = {'status': TaskStatus.PENDING.value}
    # Demoda bu kısmı atlıyoruz, gerçek arama yapmıyoruz
    # thread = threading.Thread(target=process_hotel_search, args=(task_id, data.get('location'), data.get('check_in'), data.get('check_out'), data.get('occupancy', '2'), data.get('currency', 'USD')), daemon=True)
    # thread.start()
    print(f"Simulating hotel search task {task_id}")
    update_task_status(task_id, TaskStatus.COMPLETED.value, data="Simulated hotel search data.")
    return jsonify({'task_id': task_id, 'status': TaskStatus.PENDING.value})


@app.route('/task_status/<task_id>', methods=['GET'])
def get_status(task_id):
    try:
        with task_lock:
            result = task_results.get(task_id)
        if not result:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- AI Asistanı İçin Yeni Kısımlar ---

# 1. Veri Kaynakları (Backend içinde yer alıyor)
flights_data = [
    {"id": "F001", "departure": "Istanbul", "arrival": "Ankara", "date": "2025-07-15", "price": "1200 TL"},
    {"id": "F002", "departure": "Istanbul", "arrival": "Izmir", "date": "2025-07-20", "price": "950 TL"},
    {"id": "F003", "departure": "Ankara", "arrival": "Antalya", "date": "2025-08-01", "price": "1100 TL"},
    {"id": "F004", "departure": "Izmir", "arrival": "Istanbul", "date": "2025-07-25", "price": "800 TL"},
    {"id": "F005", "departure": "Istanbul", "arrival": "Bodrum", "date": "2025-08-10", "price": "1500 TL"},
]

hotels_data = [
    {"id": "H001", "name": "Grand Hotel", "city": "Ankara", "price_per_night": "2000 TL", "rating": "4.5"},
    {"id": "H002", "name": "Deniz Pension", "city": "Izmir", "price_per_night": "800 TL", "rating": "3.8"},
    {"id": "H003", "name": "Park Hotel", "city": "Istanbul", "price_per_night": "3500 TL", "rating": "4.2"},
    {"id": "H004", "name": "Sahil Resort", "city": "Antalya", "price_per_night": "2800 TL", "rating": "4.0"},
    {"id": "H005", "name": "City Center Hotel", "city": "Istanbul", "price_per_night": "2500 TL", "rating": "3.9"},
]

# 2. LLM Modelini Tanımla (OpenAI ile!)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)


# 3. Kullanıcının Niyetini Anlama Şeması
class QueryIntent(BaseModel):
    city: str = Field(description="The city mentioned by the user, or an empty string if not specified.")
    service: str = Field(description="The type of service the user wants (hotel, flight, both, or 'unknown').")

parser = JsonOutputParser(pydantic_object=QueryIntent)

# prompt_template_string'i ayrı bir değişken olarak tanımlıyoruz
intent_prompt_template_string = """Analyze the user's request below and return the city and desired service (hotel, flight) in JSON format.
If the city is not specified, write 'unknown' or an empty string. If the service is not specified, write 'unknown'.
Be mindful of Turkish characters in city names (e.g., Istanbul, Izmir, Ankara, Antalya, Bodrum).
{format_instructions}
User request: {query}"""

# ChatPromptTemplate'i oluştururken format_instructions'ı .partial() ile dolduruyoruz
intent_prompt = ChatPromptTemplate.from_template(intent_prompt_template_string).partial(
    format_instructions=parser.get_format_instructions()
)

# intent_chain artık sadece query'yi alacak, çünkü format_instructions zaten prompt'a eklendi
intent_chain = {"query": RunnablePassthrough()} | intent_prompt | llm | parser


# 4. Veri Arama Fonksiyonu
def search_data(intent: QueryIntent):
    results = {"flights": [], "hotels": []}
    city = intent.city.lower() if intent.city else ""
    service = intent.service.lower() if intent.service else ""

    if service in ["flight", "both", "unknown", ""]:
        if city and city != "unknown":
            results["flights"] = [f for f in flights_data if city in f["departure"].lower() or city in f["arrival"].lower()]
        else:
            results["flights"] = flights_data
    if service in ["hotel", "both", "unknown", ""]:
        if city and city != "unknown":
            results["hotels"] = [h for h in hotels_data if city in h["city"].lower()]
        else:
            results["hotels"] = hotels_data
    return results

# 5. Cevap Oluşturma Prompt'u
response_prompt = ChatPromptTemplate.from_template(
    """The user's original query was: {original_query}
    Flights found based on this query: {flights_found}
    Hotels found: {hotels_found}

    Using this information, respond to the user in a natural, helpful, and warm tone.
    If no flights or hotels were found, please state that.
    Remember, you only need to provide information, not perform transactions (e.g., do not say 'I can make a reservation').
    Pay attention to grammar and natural language.
    Current date: June 11, 2025.
    """
)

# 6. AI Zincirini Oluştur
travel_assistant_chain = (
    RunnablePassthrough.assign(
        intent=intent_chain,
        original_query=lambda x: x
    )
    .assign(
        search_results=lambda x: search_data(x["intent"])
    )
    .assign(
        flights_found=lambda x: x["search_results"]["flights"],
        hotels_found=lambda x: x["search_results"]["hotels"]
    )
    | response_prompt
    | llm
)

# --- Yeni AI API Endpoint'i ---
@app.route('/ask_assistant', methods=['POST'])
def ask_assistant():
    """
    Handles incoming POST requests from the frontend, processes the user's query
    using the AI chain, and returns the assistant's response.
    This endpoint will be used by the Streamlit frontend.
    """
    user_query = request.json.get('query')
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    try:
        # Hata burada oluşuyordu. user_query'yi {"query": user_query} olarak sarmalıyoruz.
        response = travel_assistant_chain.invoke({"query": user_query}) # <<< Bu satır değişti!
        # LLM'den gelen cevabı direkt olarak döndür
        return jsonify({"answer": response.content})
    except Exception as e:
        print(f"Error processing AI request: {e}")
        return jsonify({"error": "An internal server error occurred while processing AI request."}), 500

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5001) # Port numaran 5001 ise bu şekilde kalsın