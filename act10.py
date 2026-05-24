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

print("=" * 100)
print("                         AI CHATBOT - Powered by LM Studio")
print("=" * 100)
print("Type 'exit' or press ESC to quit.")
print("Type 'clear' to reset conversation history.")
print("=" * 100)

while True:
    query = input("\nUser (Type 'exit' or press ESC to quit): ")

    if keyboard.is_pressed('Esc') or query.lower() == 'exit':
        print("\nExiting...")
        print("Program Finished.")
        break

    if query.lower() == 'clear':
        history.clear()
        print("\n Conversation history cleared.\n")
        print("=" * 100)
        continue

    if not query.strip():
        continue

    print("\nUser Input:", query)
    print('- ' * 50)

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
        history.add_ai_message(full_ai_response)

    except Exception as e:
        print(f"\n Error: {e}")
        print("Make sure LM Studio is running at http://127.0.0.1:1234")

    print('\n' + '=' * 100 + '\n')