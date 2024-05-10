import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
import genanki
import random
import time
import re
import threading

driver = webdriver.Edge()

microbial_world_url = "https://discord.com/channels/756895543942447104/1221088099614851223"
bacteria_url = "https://discord.com/channels/756895543942447104/1221091776165707837"
archaea_url = "https://discord.com/channels/756895543942447104/1221091797938471034"
eukaryotes_url = "https://discord.com/channels/756895543942447104/1221091811699851265"
viruses_url = "https://discord.com/channels/756895543942447104/1221091824551334008"
cultivating_url = "https://discord.com/channels/756895543942447104/1221091851675897978"
mvps_url = "https://discord.com/channels/756895543942447104/1221091881707110532"


CHANNELS = [microbial_world_url, bacteria_url, archaea_url, eukaryotes_url, viruses_url,
            cultivating_url, mvps_url]

basic_model = genanki.Model(
    model_id=random.randrange(1 << 30, 1 << 31),
    name='Basic Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
    ],
    templates=[
        {
            'name': 'Basic Q/A',
            'qfmt': '{{Question}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}'
        }
    ]
)

media_model = genanki.Model(
    model_id=random.randrange(1 << 30, 1 << 31),
    name='Media Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
        {'name': 'MyMedia'},
    ],
    templates=[
        {
            'name': 'Basic Q/A w img',
            'qfmt': '{{Question}}',
            'afmt': '<hr id="answer">{{Answer}}<br>{{MyMedia}}'
        }
    ]
)

wait = WebDriverWait(driver, 10)


def url_to_str(url):
    if url == CHANNELS[0]:
        return "microbial"
    elif url == CHANNELS[1]:
        return "bacteria"
    elif url == CHANNELS[2]:
        return "archaea"
    elif url == CHANNELS[3]:
        return "eukaryotes"
    elif url == CHANNELS[4]:
        return "viruses"
    elif url == CHANNELS[5]:
        return "cultivating"
    else:
        return "mvps"


def file_extension(content_type):
    if 'image/jpeg' in content_type:
        return '.jpg'
    elif 'image/png' in content_type:
        return '.png'
    elif 'image/gif' in content_type:
        return '.gif'
    elif 'image/webp' in content_type:
        return '.webp'
    else:
        return '.jpg'


def login():
    # Open Discord in the browser
    driver.get('https://discord.com')
    login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'login-button-js')))
    login_button.click()

    email_input = wait.until(EC.visibility_of_element_located((By.NAME, 'email')))
    email_input.send_keys('email')
    password_input = wait.until(EC.visibility_of_element_located((By.NAME, 'password')))
    password_input.send_keys('password')
    password_input.send_keys(Keys.RETURN)


def prepare_channel(channel_url):
    driver.get(channel_url)
    time.sleep(5)
    chat_area = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'managedReactiveScroller__08e95')))
    driver.execute_script("arguments[0].scrollTo(0, 0);", chat_area)
    time.sleep(2)


def clean_question(q):
    # Define the regex pattern to match the prefix
    begin_pattern = r'^username\s+\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+(AM|PM)\n*'

    # Use re.sub() to remove the prefix from the message
    q = re.sub(begin_pattern, '', q)

    # Remove "(edited)" from the end of the message
    q = re.sub(r'\(edited\)', '', q)

    # Remove "SPOILER" from the end of the message
    q = re.sub(r'\s*SPOILER', '', q)

    # Remove any trailing whitespace
    q = q.strip()

    return q


def extract_question(message_element, count: int):
    question = message_element.text
    print(str(count) + ": " + question)
    has_image = False

    try:
        answerElement = message_element.find_element(By.CLASS_NAME, "spoilerContent__383f3")
        try:
            answerElement.click()
            time.sleep(0.5)
            answer = answerElement.text
        except ElementClickInterceptedException:
            # element hidden by chat bar
            driver.execute_script("arguments[0].click();", answerElement)
            time.sleep(0.2)
            answer = answerElement.text
            if answer == "":
                answer = "No answer found"
    except NoSuchElementException:
        answer = "No such element found"

    if "SPOILER" in question:
        try:
            answerElement = message_element.find_element(By.XPATH, ".//img[@alt='Image']")
            image_url = answerElement.get_attribute("src")
            response = requests.get(image_url)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                print(content_type)
                image_name = 'answer_q' + str(count) + url_to_str(channel) + file_extension(content_type)
                with open(image_name, 'wb') as f:
                    f.write(response.content)
                    print("Image downloaded successfully")
                    answer = image_name
                    has_image = True
            else:
                answer = "Failed to download image"
                print(answer)
        except NoSuchElementException:
            pass

    print("answer to question " + str(count) + ": " + answer)

    question = clean_question(question)

    return [question, answer, has_image]


def make_flashcard(question: str, answer: str, has_image: bool):
    if has_image:
        note_model = media_model
        note_fields = [question, "", '<img src="' + answer + '">']
    else:
        note_model = basic_model
        note_fields = [question, answer]

    note = genanki.Note(
        model=note_model,
        fields=note_fields
    )
    print("flashcard made")
    return note

def process_channel(channel):
    channel_deck = genanki.Deck(
        random.randrange(1 << 30, 1 << 31),
        'BIOL240::' + url_to_str(channel)
    )

    files = []

    prepare_channel(channel)

    messages = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//*[starts-with(@id, 'chat-messages')]")))
    count = 1
    begin = True
    for message in messages:

        # the first message is the channel beginning
        if begin:
            begin = False
            continue

        note_data = extract_question(message, count)
        if note_data[2]:
            files.append(note_data[1])

        flashcard = make_flashcard(note_data[0], note_data[1], note_data[2])
        channel_deck.add_note(flashcard)

        count += 1
    channel_package = genanki.Package(channel_deck)
    channel_package.media_files = files
    channel_package.write_to_file(url_to_str(channel) + ".apkg")

login()
time.sleep(5)

threads = []

for channel in CHANNELS:
    thread = threading.Thread(target=process_channel, args=(channel,))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
