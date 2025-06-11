import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.pydantic_v1 import BaseModel, Field

# Load the API key from the .env file
load_dotenv()

# --- 1. Data Sources (Example) ---
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

# --- 2. Define the LLM Model (with OpenAI!) ---
# The OPENAI_API_KEY environment variable should be loaded by python-dotenv.
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0) # temperature=0 for more consistent responses

# --- 3. Schema for Understanding User Intent ---
class QueryIntent(BaseModel):
    city: str = Field(description="The city mentioned by the user, or an empty string if not specified.")
    service: str = Field(description="The type of service the user wants (hotel, flight, both, or 'unknown').")

parser = JsonOutputParser(pydantic_object=QueryIntent)

intent_prompt = ChatPromptTemplate.from_template(
    """Analyze the user's request below and return the city and desired service (hotel, flight) in JSON format.
    If the city is not specified, write 'unknown' or an empty string. If the service is not specified, write 'unknown'.
    Be mindful of Turkish characters in city names (e.g., Istanbul, Izmir, Ankara, Antalya, Bodrum).
    {format_instructions}
    User request: {query}"""
)

intent_chain = {"query": RunnablePassthrough()} | intent_prompt | llm | parser

# --- 4. Data Search Function ---
def search_data(intent: QueryIntent):
    results = {"flights": [], "hotels": []}
    city = intent.city.lower() if intent.city else "" # Handle empty string for city
    service = intent.service.lower() if intent.service else "" # Handle empty string for service

    # Flight search
    if service in ["flight", "both", "unknown", ""]:
        if city and city != "unknown":
            results["flights"] = [f for f in flights_data if city in f["departure"].lower() or city in f["arrival"].lower()]
        else:
            results["flights"] = flights_data # Show all flights if no city is specified

    # Hotel search
    if service in ["hotel", "both", "unknown", ""]:
        if city and city != "unknown":
            results["hotels"] = [h for h in hotels_data if city in h["city"].lower()]
        else:
            results["hotels"] = hotels_data # Show all hotels if no city is specified

    return results

# --- 5. Response Generation Prompt ---
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

# --- 6. Build the Chain ---
chain = (
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

# --- Usage ---
print("Hello! I'm your travel assistant. How can I help you today?")
print("You can type 'exit' to quit.")
while True:
    user_query = input("You: ")
    if user_query.lower() in ["exit", "quit", "bye", "goodbye"]:
        print("Assistant: Goodbye! Have a great day.")
        break
    try:
        response = chain.invoke(user_query)
        print(f"Assistant: {response.content}") # The response from the LLM is usually in the .content attribute
    except Exception as e:
        print(f"Assistant: I'm sorry, an error occurred. Details: {e}")
        print("Please ensure your OpenAI API key is correct and you have an internet connection.")