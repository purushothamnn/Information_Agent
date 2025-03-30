import streamlit as st
import speech_recognition as sr
import os
import tempfile
from PIL import Image
import requests
import base64
import google.generativeai as genai
from io import BytesIO

# Set page title and layout
st.set_page_config(page_title="Voice to Image Generator", layout="wide")
st.title("Voice Command to Image Generator")

# Set up Gemini API key configuration - properly handled with secrets
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]  # This should be the key name in secrets, not the key value
else:
    # Fallback UI for API key input if not in secrets
    GEMINI_API_KEY = st.sidebar.text_input("Enter Gemini API Key:", type="password")
    if not GEMINI_API_KEY:
        st.warning("Please enter your Gemini API key to continue.")
        st.stop()

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Set up the Gemini model
model = genai.GenerativeModel('gemini-1.5-pro')

# Function to transcribe audio to text
def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError:
            return "API unavailable"

# Function to generate image based on a prompt
def generate_image(prompt):
    # Check for Stability API key
    if "STABILITY_API_KEY" in st.secrets:
        STABILITY_API_KEY = st.secrets["STABILITY_API_KEY"]
    else:
        # Fallback UI for API key input if not in secrets
        STABILITY_API_KEY = st.sidebar.text_input("Enter Stability API Key:", type="password")
        if not STABILITY_API_KEY:
            st.warning("Please enter your Stability API key to continue.")
            st.stop()
    
    # Example using Stable Diffusion API
    API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            image_b64 = data["artifacts"][0]["base64"]
            image = Image.open(BytesIO(base64.b64decode(image_b64)))
            return image
        else:
            st.error(f"Error: {response.status_code}")
            if response.text:
                st.error(f"Details: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error generating image: {e}")
        return None

# Function to get information about the prompt using Gemini
def get_information(prompt):
    try:
        response = model.generate_content(f"Provide a brief, informative summary about {prompt}. Include interesting facts and key information in 3-4 paragraphs.")
        return response.text
    except Exception as e:
        st.error(f"Error getting information: {e}")
        return "Could not retrieve information at this time."

# Sidebar for instructions
with st.sidebar:
    st.header("Instructions")
    st.write("1. Click the 'Record Voice Command' button")
    st.write("2. Speak your command clearly")
    st.write("3. Wait for the app to process your request")
    st.write("4. View the generated image and information")
    
    st.header("About")
    st.write("This app uses speech recognition to convert your voice command into text, then generates an image based on that command and provides information using Google's Gemini API.")

# Main content area with two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Voice Input")
    
    # Button to record audio
    if st.button("Record Voice Command"):
        try:
            with st.spinner("Recording... Speak now"):
                # Create a temporary file to store the audio
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                    temp_audio_path = temp_audio.name
                
                # Record audio
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source)
                    audio = r.listen(source, timeout=5)
                    
                    # Save audio to the temporary file
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio.get_wav_data())
                
                # Transcribe the audio
                st.session_state.transcription = transcribe_audio(temp_audio_path)
                os.remove(temp_audio_path)
        except Exception as e:
            st.error(f"Error recording audio: {e}")
            st.session_state.transcription = "Error recording audio. Please try again."
    
    # Display the transcription
    if "transcription" in st.session_state:
        st.subheader("Transcribed Command:")
        st.write(st.session_state.transcription)
        
        if st.session_state.transcription not in ["Could not understand audio", "API unavailable", "Error recording audio. Please try again."]:
            with st.spinner("Generating image and information..."):
                # Generate the image based on the transcription
                st.session_state.image = generate_image(st.session_state.transcription)
                
                # Get information about the prompt
                st.session_state.info = get_information(st.session_state.transcription)

with col2:
    st.header("Results")
    
    # Display the generated image
    if "image" in st.session_state and st.session_state.image is not None:
        st.subheader("Generated Image:")
        st.image(st.session_state.image, use_column_width=True)
    
    # Display information about the prompt
    if "info" in st.session_state:
        st.subheader("Information:")
        st.write(st.session_state.info)

# Manual text input option
st.header("Or Type Your Prompt")
manual_prompt = st.text_input("Enter your prompt here:")
if st.button("Generate from Text"):
    if manual_prompt:
        with st.spinner("Generating image and information..."):
            st.session_state.transcription = manual_prompt
            st.session_state.image = generate_image(manual_prompt)
            st.session_state.info = get_information(manual_prompt)