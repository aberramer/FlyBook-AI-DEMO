import streamlit as st
from datetime import datetime
import requests # Backend ile iletişim için gerekli
# from ai.travel_assistant import TravelAssistant # Kaldırıldı
# from ai.travel_summary import TravelSummary # Kaldırıldı
# from api.api_client import TravelAPIClient # Kaldırıldı - Artık kendi backend'imizi çağıracağız
# from ai.research_assistant import ResearchAssistant # Kaldırıldı
from constants import *
import stripe # type: ignore

# Stripe API Key - KALACAK
stripe.api_key = 'sk_test_51ROFGB01KCzUb8NX92iLWF6E5n4lpDX7X6elev7crJnbdmn6rZX1ffvfocCPOh78fH5aaYUWQd6wAhzzeKzK3mwo00Ruy4pxpR'

# Stripe Checkout - KALACAK
def create_checkout_session(amount):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Travel Assistant Usage',
                    },
                    'unit_amount': amount * 100,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:8501?success=true',
            cancel_url='http://localhost:8501?canceled=true',
        )
        return session.url
    except Exception as e:
        return str(e)

# Information Bubble - METNİ GÜNCELLİYORUZ AMA KALDIRMIYORUZ
if 'show_bubble' not in st.session_state:
    st.session_state.show_bubble = True

if st.session_state.show_bubble:
    # Metni güncelliyoruz: Artık hem uçuş hem otel var
    st.info("This is a demo version of FlyBook AI. You can now find flights and hotels! 💡 How to Use FlyBook AI: Quickly find flights, hotels, and restaurants without filter limitations. Click [here](#information) for more details.")
    if st.button("Got it!"):
        st.session_state.show_bubble = False

# Information Section - OLDUĞU GİBİ KALACAK
def show_information():
    st.header("ℹ️ How to Use FlyBook AI")
    st.markdown("""
        FlyBook AI allows you to search for flights, hotel reservations, and restaurant recommendations in a simple and efficient way.
        Unlike other platforms, FlyBook AI uses web scraping to overcome filtering limitations.
        **Please Note:**
        - We only provide flight, hotel, and restaurant information. Other services like rental gear for activities (e.g., scuba diving) are not available.
        - Filter limitations commonly seen on other sites do not apply here.
        - We do not support pet-friendly or specific amenities filtering, but we aim to provide comprehensive options.
        """)

with st.sidebar:
    if st.button("ℹ️ Information"):
        show_information()

# ResearchAssistant._initialize_vector_store() # Orijinal kodda vardı, AI asistanına taşıdığımız için kaldırıldı.

# Payment Category in Sidebar - OLDUĞU GİBİ KALACAK
with st.sidebar:
    st.header("💳 Payment")
    if st.button("Pay $3"):
        checkout_url = create_checkout_session(3)
        st.markdown(f'[Proceed to Payment]({checkout_url})')
    if st.button("Pay $6"):
        checkout_url = create_checkout_session(6)
        st.markdown(f'[Proceed to Payment]({checkout_url})')

# format_date fonksiyonu hala kullanılabilir, API'ye gönderilmese bile display için işe yarar
def format_date(date_str):
    """Format date string for display and API calls"""
    if isinstance(date_str, datetime):
        return date_str.strftime("%B %d, %Y")
    return date_str

# initialize_session_state fonksiyonu
def initialize_session_state():
    """Initialize all session state variables"""
    if 'search_requirements' not in st.session_state:
        st.session_state.search_requirements = ""
    if 'travel_assistant_active' not in st.session_state: # Zincirin aktif olup olmadığını işaretlemek için bayrak
        st.session_state.travel_assistant_active = False
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'summary' not in st.session_state:
        st.session_state.summary = None
    # Research assistant ile ilgili kısımları kaldır
    # if 'research_assistant' not in st.session_state:
    #     st.session_state.research_assistant = None
    # if 'research_messages' not in st.session_state:
    #     st.session_state.research_messages = []
    if 'parsed_data' not in st.session_state: # Bu artık kullanılmayabilir ama tutmak istersen kalabilir
        st.session_state.parsed_data = None
    if 'progress_bar' not in st.session_state:
        st.session_state.progress_bar = None

# display_parsed_travel_details fonksiyonu kaldırıldı çünkü artık doğrudan AI'dan cevap alıyoruz
# def display_parsed_travel_details(parsed_data):
#     pass # İçeriği boşaltıldı

def search_travel_options(travel_description, progress_container):
    """
    Sends the user's travel description to the local Flask backend's AI endpoint
    and retrieves the AI assistant's combined response (summary + initial chat).
    """
    with progress_container.status("✨ Finding the best options for you...", state="running", expanded=True):
        my_bar = st.progress(0)
        try:
            st.write(" - 🧠 Sending your request to AI backend...")
            my_bar.progress(0.2)

            # Backend'deki Flask uygulamasının yeni AI endpoint'ine POST isteği gönderiyoruz
            backend_url = "http://localhost:5001/ask_assistant"
            payload = {"query": travel_description}

            response = requests.post(backend_url, json=payload)
            response.raise_for_status() # HTTP hata durumlarını yakala (4xx veya 5xx)

            my_bar.progress(0.8)

            # Cevabı JSON olarak al
            data = response.json()
            ai_answer = data.get("answer", "No answer received from assistant.")

            st.success("Search completed!")

            # Backend'den gelen AI cevabını doğrudan özet olarak kullan
            st.session_state.summary = ai_answer
            
            # travel_assistant'ın artık aktif olduğunu işaret et
            st.session_state.travel_assistant_active = True

            # Set flag to switch to results tab
            st.session_state.switch_to_results = True
            return True

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the AI backend. Please ensure the backend (app.py) is running on http://localhost:5000 in a separate terminal.")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred with the request to the backend: {e}")
            return False
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            return False

def render_chat_interface(messages, is_assistant_active, input_placeholder):
    """Render a chat interface with message history and input"""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Show suggested prompts for empty chat
    if not messages:
        st.markdown("### Suggested Questions:")
        suggested_prompts_list = [
            "What flights are available to Istanbul?",
            "Can you find a hotel in Ankara?",
            "Are there any affordable hotels in Izmir?",
            "Tell me about flights to Antalya.",
            "Can you look for both flights and hotels?"
        ]
        cols = st.columns(2)
        for i, prompt_text in enumerate(suggested_prompts_list):
            if i % 2 == 0:
                with cols[0]:
                    st.markdown(f"- {prompt_text}")
            else:
                with cols[1]:
                    st.markdown(f"- {prompt_text}")

    # Chat input
    if prompt := st.chat_input(input_placeholder, disabled=not is_assistant_active): # Asistan aktif değilse inputu kapat
        # Add user message
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get and display AI response from backend for chat
        with st.chat_message("assistant"):
            try:
                # Backend'e ikinci kez istek gönderiyoruz, bu sefer chat için
                backend_url = "http://localhost:5000/ask_assistant"
                payload = {"query": prompt}
                response = requests.post(backend_url, json=payload)
                response.raise_for_status()
                data = response.json()
                ai_response_content = data.get("answer", "No answer received.")
                st.markdown(ai_response_content)
                messages.append({"role": "assistant", "content": ai_response_content})
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the AI backend for chat. Please ensure the backend is running.")
            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred during chat request: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred during chat: {str(e)}")


def render_search_tab():
    """Render the search tab content"""
    st.header("🌍 Share Your Travel Dreams With Us!")

    travel_description = st.text_area(
        "✈️ Tell us what kind of trip you have in mind—whether it’s a relaxing getaway, a romantic escape, or an adventurous journey! ",
        height=200,
        placeholder="E.g., I'm looking for a flight to Antalya next month and a nice hotel there."
    )

    if st.button("Plan My Trip"):
        if not travel_description:
            st.warning("Please describe your trip!")
            st.stop()

        progress_container = st.container()
        search_travel_options(travel_description, progress_container)


def render_results_tab():
    """Render the results tab content"""
    # travel_assistant_active bayrağını kontrol ediyoruz
    if not st.session_state.get('travel_assistant_active'):
        st.info("👋 No trip details available yet!")
        st.markdown("Please tell us your travel plans in the 'Search' tab to see results here.")

        with st.expander("Preview what you'll get", expanded=False):
            st.markdown(PREVIEW_SUMMARY) # Bu sabit constants.py'den geliyorsa kalabilir
    else:
        with st.expander("Travel Summary", expanded=True):
            st.markdown("### Flight and Hotel Details")
            if 'summary' in st.session_state and st.session_state.summary:
                st.markdown(st.session_state.summary)
            else:
                st.info("Summary not available yet. Please try searching for a trip.")

        with st.expander("Travel Planning Assistant", expanded=True):
            render_chat_interface(
                st.session_state.chat_messages,
                st.session_state.travel_assistant_active, # Buraya bayrağı gönderiyoruz
                "Ask me anything about your trip..."
            )

def render_research_tab():
    """Render the research tab content"""
    # Araştırma asistanı etkin olmadığı için basitleştirilmiş mesaj
    st.info("Research Assistant is not active in this demo version.")
    st.markdown("This tab would normally provide more detailed research capabilities about your destination.")

def main():
    """Main application entry point"""
    # Initialize services - Artık backend tarafından yönetiliyor, frontend'de APIClient'a gerek yok
    # global api_client, travel_summary # Kaldırıldı
    # api_client = TravelAPIClient() # Kaldırıldı
    # travel_summary = TravelSummary() # Kaldırıldı

    # Initialize session state
    initialize_session_state()

    # Main UI
    st.title("FlyBook AI - Demo")

    # Create main tabs
    search_tab, results_tab, research_tab = st.tabs(["Search", "Results & Planning", "Research"])

    # Render tab contents
    with search_tab:
        render_search_tab()

    with results_tab:
        render_results_tab()

    with research_tab:
        render_research_tab()

    # Handle tab switching after search
    if hasattr(st.session_state, 'switch_to_results') and st.session_state.switch_to_results:
        st.session_state.switch_to_results = False
        # st.tabs'ın aktif sekmesini programatik olarak değiştirmek için doğrudan bir yol yok.
        # Genellikle kullanıcıya manuel olarak geçmesini söylemek veya yeniden yönlendirmek gerekir.
        # Bu satır çalışmazsa kaldırılabilir.
        # results_tab._active = True # Bu satır Streamlit'in içsel bir mekanizmasıdır ve güvenilir değildir.

if __name__ == "__main__":
    main()