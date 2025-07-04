import os
import google.generativeai as genai
from dotenv import load_dotenv
import re
import ast

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

#if not api_key:
    #raise ValueError("API key not found.")


genai.configure(api_key=api_key)


SERVICES = [
    "Air Filter Check",
    "Battery Check",
    "Brake Inspection",
    "Cabin Filter Replacement",
    "Comprehensive Diagnostic Check",
    "Exhaust System Inspection",
    "Fluid Levels Check",
    "Fuel System Inspection",
    "Lights and Wipers Check",
    "Oil Change",
    "Oil Filter Replacement",
    "Spark Plugs Replacement",
    "Steering and Suspension Check",
    "Timing Belt Inspection",
    "Transmission Check",
    "Tyre Condition and Alignment Check",
    "Tyre Pressure Check",
    "Underbody Inspection",
    "Visual Inspection",
    "Wheel Alignment and Balancing"
]


def get_matching_services(user_input):
    prompt = f"""
You're a helpful assistant. A supervisor has written: "{user_input}".
Which of these services are most relevant?

Available services:
{', '.join(SERVICES)}

Respond with a plain Python list of the most relevant service names.
Only include services from the list. Do NOT use code blocks.
"""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash') 
        response = model.generate_content(prompt)
        text_response = response.text.strip()

    
        cleaned_text = re.sub(r"```(?:python)?\n([\s\S]+?)```", r"\1", text_response)

        
        matches = ast.literal_eval(cleaned_text)
        return matches

    except Exception as e:
        print("Error parsing Gemini response:", e)
        print("Raw response:", response.text if 'response' in locals() else "No response.")
        return []


if __name__ == "__main__":
    user_input = input("Enter a description of the issue or damage: ")
    services = get_matching_services(user_input)
    if services:
        print("\n Suggested services:")
        for s in services:
            print("-", s)
    else:
        print("\n No services matched or an error occurred.")
