import sys
from openai import OpenAI
import keyboard
from langchain_community.chat_message_histories import ChatMessageHistory

# Connect to LM Studio Local server
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

# Initialize the history object
history = ChatMessageHistory()

# Read the code and save to output file first
with open("act10.py", "r") as code_file:
    code_content = code_file.read()

output = open("act10_output.txt", "w", encoding="utf-8")
output.write(code_content)
output.write("\n" + "=" * 100 + "\n")
output.write("                         CONVERSATION OUTPUT\n")
output.write("=" * 100 + "\n\n")
output.close()

# Reopen in append mode
output = open("act10_output.txt", "a", encoding="utf-8")

print("=" * 100)
print("                         AI CHATBOT - Powered by LM Studio")
print("=" * 100)
print("Type 'exit' or press ESC to quit.")
print("=" * 100)

while True:
    query = input("\nUser (Type 'exit' or press ESC to quit): ")

    if keyboard.is_pressed('Esc') or query.lower() == 'exit':
        print("\nExiting...")
        print("Program Finished.")
        output.write("Exiting...\nProgram Finished.")
        output.close()
        break

    if not query.strip():
        continue

    print("\nUser Input:", query)
    print('- ' * 50)
    output.write(f"\nUser Input: {query}\n")
    output.write('- ' * 50 + "\n")

    history.add_user_message(query)

    messages_with_history = []
    for m in history.messages:
        role = "user" if m.type == "human" else "assistant"
        messages_with_history.append({"role": role, "content": m.content})

    try:
        response = client.chat.completions.create(
            model="google/gemma-4-e4b",
            messages=messages_with_history
        )
        full_ai_response = response.choices[0].message.content
        print("\nAI Response:\n")
        print(full_ai_response)
        output.write(f"\nAI Response:\n\n{full_ai_response}\n")
        history.add_ai_message(full_ai_response)

    except Exception as e:
        print(f"\n Error: {e}")
        print("Make sure LM Studio is running at http://127.0.0.1:1234")

    print('\n' + '=' * 100 + '\n')
    output.write('\n' + '=' * 100 + '\n')