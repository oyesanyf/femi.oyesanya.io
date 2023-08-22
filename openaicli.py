import openai
import sys

openai.api_key = "YOUR API KEY"

def input(prompt):
    print(prompt, end='', file=sys.stderr, flush=True)
    return sys.stdin.readline()

def openAIQuery(query):
    msg = [{"role": "user", "content" : query },]
    for data in msg:
      for key, value in data.items():
          if key !="role" and value !="user":
             print(f"Key: {key}, Value: {value}")
             log_message ("Prompt injection attempt, only role=user is allowed")
             quit()  
          else:
              response = openai.ChatCompletion.create( model="gpt-3.5-turbo", messages = msg, temperature=0.8,   top_p=1, frequency_penalty=0, presence_penalty=0,  )
              return response


def main():
    if not openai.api_key:
        print(f"api_key is not set")
        log_message("OpenAI API key not set...")
        log_message("Ending session...........")
        quit()

while True:
    try:
        query = input("Enter question: ")
        response = openAIQuery(query)
        print(response)     
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        continue

if __name__ == "__main__":
    main()
