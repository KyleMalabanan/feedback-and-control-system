from openai import OpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
# Setup the Local Client
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1", 
    api_key="lm-studio"
)
history = ChatMessageHistory()
# Matching the header from the image - MODIFIED NAME HERE
print("Chatbot initialized for Kyle Malabanan.") # <-- Changed name here
print("Type 'exit' anytime to stop.\n")
while True:
    query = input("User Input: ") # This creates the input box
    if query.lower() == "exit":
        print("\nExiting...")
        print("Program Finished.")
        break
    if not query.strip():
        continue
    # 1. Print the User Input back to the console with the dashed line
    print(f"User Input: {query}") 
    print("- " * 50)
    history.add_user_message(query)
    messages_with_history = []
    for m in history.messages:
        role = "user" if m.type == "human" else "assistant"
        messages_with_history.append({
            "role": role,
            "content": m.content
        })
    try:
        # 2. Call the Llama model
        stream = client.chat.completions.create(
            model="lmstudio-community/Llama-3.2-3B-Instruct-GGUF", 
            messages=messages_with_history,
            stream=True
        )
        full_ai_response = ""
        # 3. Stream the response
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_ai_response += content
        history.add_ai_message(full_ai_response)
        # 4. Print the double-line separator after the AI response
        print("\n \n" + "=" * 100 + "\n")
    except Exception as e:
        print(f"\n Error: {e}")
        print("=" * 100 + "\n")

