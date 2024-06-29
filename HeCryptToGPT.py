# Importing necessary libraries
# POC by Femi Oyesanya

import socket
import tenseal as ts 
import asyncio
import os
import logging
from openai import AsyncOpenAI, OpenAIError
from tqdm import tqdm  # tqdm for progress tracking

# Set up logging for error handling and activity logging
log_filename = 'server_client.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)

# Load OpenAI key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logging.error("OpenAI API key not found in environment variables.")
    raise EnvironmentError("OpenAI API key is empty.")

# Instantiate the AsyncOpenAI client
openai_client = AsyncOpenAI(api_key=openai_api_key)

# Function to create TenSEAL context for encryption
def create_context():
    logging.info("Creating TenSEAL context for encryption.")
    context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60])
    context.global_scale = 2**40
    context.generate_galois_keys()
    logging.info("TenSEAL context created successfully.")
    return context

# Function to encrypt a prompt using TenSEAL
def encrypt_prompt(prompt, context):
    logging.info(f"Encrypting prompt: {prompt}")
    plaintext = [ord(c) for c in prompt]
    encrypted_prompt = ts.ckks_vector(context, plaintext)
    serialized_prompt = encrypted_prompt.serialize()
    logging.info("Prompt encrypted successfully.")
    return serialized_prompt

# Function to decrypt a response using TenSEAL
def decrypt_response(serialized_response, context):
    logging.info("Decrypting response.")
    encrypted_response = ts.ckks_vector_from(context, serialized_response)
    decrypted_response = encrypted_response.decrypt()
    response_string = ''.join([chr(int(round(num))) for num in decrypted_response])
    logging.info(f"Response decrypted successfully: {response_string}")
    return response_string

# Coroutine to receive data from a client
async def receive_data(reader, expected_length):
    logging.info("Receiving data from client.")
    data = b""
    while len(data) < expected_length:
        packet = await reader.read(4096)
        if not packet:
            break
        data += packet
        logging.info(f"Packet received (length: {len(packet)} bytes)")
    logging.info(f"Total data received (length: {len(data)} bytes)")
    return data

# Coroutine to handle API calls with error handling
async def self_healing_call(api_call, **kwargs):
    try:
        return await api_call(**kwargs)
    except OpenAIError as e:
        logging.error(f"API Error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        return None

# Coroutine to extract data from chunks using OpenAI API
async def extract_data_from_chunks(chunks, client):
    try:
        structured_info = ""
        for chunk in tqdm(chunks, desc="Processing chunks"):
            prompt = f"""
            You are an AI model with expertise in handling user queries accurately and securely.

            {chunk}
            """
            response = await self_healing_call(
                client.chat.completions.create,
                messages=[
                    {"role": "system", "content": "You are an expert LLM prompt engineer with deep knowledge of passing encrypted prompt messages to the LLM, and the receiver will decrypt the response."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4",
                max_tokens=2000,
                top_p=0.95,
                temperature=0.3,
                n=1,
                stop=None
            )
            if response and response.choices and response.choices[0].message.content:
                structured_info += response.choices[0].message.content.strip() + "\n"
        return structured_info
    except ValueError as e:
        error_message = f"Input Error: {str(e)}"
        logging.error(error_message)
        return error_message
    except OpenAIError as e:
        error_message = f"API Error: {str(e)}"
        logging.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected Error: {str(e)}"
        logging.error(error_message)
        return error_message

# Coroutine to handle communication with a client
async def handle_client(reader, writer, context):
    try:
        logging.info("Handling new client.")
        data_length_packet = await reader.read(8)
        expected_length = int.from_bytes(data_length_packet, byteorder='big')
        logging.info(f"Expected data length: {expected_length} bytes")
        
        serialized_prompt = await receive_data(reader, expected_length)
        logging.info(f"Serialized prompt received (length: {len(serialized_prompt)} bytes)")

        # Decrypt the prompt for chunking
        encrypted_prompt = ts.ckks_vector_from(context, serialized_prompt)
        decrypted_prompt = encrypted_prompt.decrypt()
        prompt_text = ''.join([chr(int(round(num))) for num in decrypted_prompt])

        # Split the prompt text into smaller chunks
        chunks = [prompt_text[i:i+1000] for i in range(0, len(prompt_text), 1000)]

        # Send the chunks to OpenAI API and get the response
        logging.info("Sending encrypted prompt to OpenAI API.")
        response_text = await extract_data_from_chunks(chunks, openai_client)

        # Encrypt the response text
        plaintext_response = [ord(c) for c in response_text]
        encrypted_response = ts.ckks_vector(context, plaintext_response)
        serialized_response = encrypted_response.serialize()
        logging.info(f"Serialized encrypted response (length: {len(serialized_response)} bytes)")

        response_length_packet = len(serialized_response).to_bytes(8, byteorder='big')
        writer.write(response_length_packet)
        await writer.drain()

        writer.write(serialized_response)
        await writer.drain()
        logging.info("Encrypted response sent back to client.")

    except Exception as e:
        logging.error(f"Error handling client: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

# Coroutine to start the server and handle incoming connections
async def server_task(context):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, context),
        "127.0.0.1", 9999
    )
    for _ in tqdm(range(10), desc="Starting server", unit="step"):
        await asyncio.sleep(0.1)
    logging.info(f"Server started on port {server.sockets[0].getsockname()[1]}")
    async with server:
        await server.serve_forever()

# Coroutine to handle client interactions
async def client_task(context):
    while True:
        prompt = input("Enter your prompt (or type 'exit' to quit): ")
        if prompt.lower() == 'exit':
            break

        # Encrypt the prompt and split it into chunks
        encrypted_chunks = []
        for i in range(0, len(prompt), 1000):
            chunk = prompt[i:i+1000]
            serialized_chunk = encrypt_prompt(chunk, context)
            encrypted_chunks.append(serialized_chunk)

        reader, writer = await asyncio.open_connection("127.0.0.1", 9999)
        try:
            for serialized_prompt in encrypted_chunks:
                prompt_length_packet = len(serialized_prompt).to_bytes(8, byteorder='big')
                writer.write(prompt_length_packet)
                await writer.drain()
                logging.info(f"Sending prompt length to server: {len(serialized_prompt)} bytes")

                writer.write(serialized_prompt)
                await writer.drain()
                logging.info("Encrypted prompt sent to server.")

            response_text = ""
            for _ in encrypted_chunks:
                response_length_packet = await reader.read(8)
                expected_response_length = int.from_bytes(response_length_packet, byteorder='big')
                logging.info(f"Expected response length: {expected_response_length} bytes")
                serialized_response = await receive_data(reader, expected_response_length)
                logging.info(f"Serialized response received (length: {len(serialized_response)} bytes)")
                response_text += decrypt_response(serialized_response, context)

            print(response_text)

        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

# Main function to run the asyncio event loop
async def main():
    context = create_context()
    server = asyncio.create_task(server_task(context))
    await asyncio.sleep(2)
    await client_task(context)
    server.cancel()
    await server

# Entry point to run the main function
if __name__ == "__main__":
    asyncio.run(main())
