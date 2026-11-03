from groq import Groq
import dotenv

dotenv.load_dotenv()
client = Groq()

completion = client.chat.completions.create(
    model="openai/gpt-oss-20b",  # Provide a valid model identifier
    messages=[
        {
            "role": "user",
            "content": "Explain the concept of quantum computing in one sentence."
        }
    ],
    temperature=0.7,
    max_tokens=1024,
)

# Print the text response
print(completion.choices[0].message.content)