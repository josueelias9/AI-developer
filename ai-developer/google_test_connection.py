# Set GOOGLE_API_KEY as an environment variable (do not hardcode keys here)


import getpass
import os


from google import genai
import os


from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=1.0,  # Gemini 3.0+ defaults to 1.0
    max_tokens=None,
    google_api_key=os.environ["GOOGLE_API_KEY"],
    timeout=None,
    max_retries=2,
    # other params...
)

a = model.invoke("Write a poem about the moon.")
print(a)
