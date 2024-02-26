#--web true
#--param OPENAI_API_KEY $OPENAI_API_KEY
#--param OPENAI_API_HOST $OPENAI_API_HOST

from openai import AzureOpenAI
import re
import requests
import socket

ROLE = """
When requested to write code, pick Python.
When requested to show chess position, always use the FEN notation.
When showing HTML, always include what is in the body tag, 
but exclude the code surrounding the actual content. 
So exclude always BODY, HEAD and HTML .
"""

MODEL = "gpt-35-turbo"
AI = None

def req(msg):
    return [{"role": "system", "content": ROLE}, 
            {"role": "user", "content": msg}]

def ask(input):
    comp = AI.chat.completions.create(model=MODEL, messages=req(input))
    if len(comp.choices) > 0:
        content = comp.choices[0].message.content
        return content
    return "ERROR"

#
def generic_search(text, pattern):
    words = text.split(' ')
    for word in words:
        match = re.match(pattern, word)
        if match:
            return re.match(pattern, word).group()
    return ''

def search_email_address(text):
    return generic_search(text, r'^[a-z0-9]+[\._\'\-]?[a-z0-9]+[@]\w+[.]\w{2,3}$')

def search_domain(text):
    return generic_search(text, r'(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}')

def message_on_slack(msg):
    url = 'https://nuvolaris.dev/api/v1/web/utils/demo/slack'
    response = requests.get(url, params={'text': msg})
    if response.status_code == 200:
        print('ok')
    else:
        print(f'Error on slack call: {response.text}')

def there_is_an_email_address(input):
    return bool(search_email_address(input))

def there_is_a_domain(input):
    return bool(search_domain(input))

def is_a_chess_request(input):
    return False

def hello_on_slack(input):
    mail = search_email_address(input)
    message_on_slack(f'hello to {mail}')
    return f'I say hello on slack for {mail}'

def validate_email(input):
    mail = search_email_address(input)
    if mail:
        url = f'https://api.usebouncer.com/v1.1/email/verify'
        token = ('', 'ZnPBfGaYU27DsDyrb5BtZ5VQ5126l02daQhQjWJY')
        response = requests.get(url, params={'email': mail}, auth=token)
        if response.status_code == 200:
            data = response.json()
            status = data['status']
            if status == 'deliverable':
                return 'The mail is valid and exists'
            elif status == 'undeliverable':
                message_on_slack(f'{mail} is fake')
                return 'The mail does not exist'
            else:
                return 'The mail validity is unknown'
        else:
            return 'I cannot verify the email (maybe service is down)'
    else:
        return 'The email address is not valid, provide a valid one.'

def resolve_domain(input):
    domain = search_domain(input)
    ip = socket.gethostbyname(domain)
    return f"Assuming {domain} has IP address {ip}, answer to this question: {input}"

def main(args):
    global AI
    (key, host) = (args["OPENAI_API_KEY"], args["OPENAI_API_HOST"])
    AI = AzureOpenAI(api_version="2023-12-01-preview", api_key=key, azure_endpoint=host)

    input = args.get("input", "")
    if input == "":
        res = {
            "output": "Welcome to the OpenAI demo chat",
            "title": "OpenAI Chat",
            "message": "You can chat with OpenAI."
        }
    else:
        res = {}
        if there_is_an_email_address(input):
            output = hello_on_slack(input)
            output += '\n'
            output += validate_email(input)
        elif there_is_a_domain(input):
            new_input = resolve_domain(input)
            output = ask(new_input)
        else:
            output = ask(input)

        print('- ask:', output)
        res['output'] = output

    return {"body": res }
