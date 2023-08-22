from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
import pprint
import google.generativeai as palm
import sys

palm.configure(api_key='YOUR KEY')
models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
model = models[0].name
print(model)

def input(prompt):
    print(prompt, end='', file=sys.stderr, flush=True)
    return sys.stdin.readline()

while True:
    try:
        query = input("Enter question: ")       
        completion = palm.generate_text(model=model,prompt=query,temperature=0,max_output_tokens=800,)
        print(completion.result) #  'cold.'
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        continue

if __name__ == "__main__":
    main()


   
    
           


   
