import openai
import sys
import os
import datetime
import logging

openai.api_key = os.getenv("OPENAI_API_KEY")

def input(prompt):
    print(prompt, end='', file=sys.stderr, flush=True)
    return sys.stdin.readline()


def setup_logging():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    log_filename = f"ai_{current_date}.log"

    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def log_message(obj):
    logging.info(repr(obj))


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
              #print(response.choices[0].message.content)
              res = (response.choices[0].message.content)
              log_message("The response meesagefrom chatgpt is " +  res)
              return (str(res))
     
def runall(query):
    queryLen = len(query)
    log_message("The prompt meesage submitted to chatgpt is " + query)
    # check query length
    if queryLen < 20:
        log_message("prompt message is too short")
        print("Your input to chatgpt must be greater than 20 characters, try again")
        log_message("Ending session...........")
        quit()
    else:
        print("You can proceed with your input")
        response = openAIQuery(query)
        return response


def main():
    if not openai.api_key:
        print(f"api_key is not set")
        log_message("OpenAI API key not set...")
        log_message("Ending session...........")
        quit()



setup_logging()
while True:
    try:
        query = input("Enter question: ")
        msg = runall(query)
        querymsglow = (msg)
        print(querymsglow)
        prompt = querymsglow.lower()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        continue

if __name__ == "__main__":
    main()
