# mikusec
Chatbot in Brazilian Portuguese based on Ontology to support blockchain Q&amp;A integrated with Telegram

# Requirements

- Jupyter Notebook, Google Colab, AWS Sagemaker or a standard Python 3 environment
- Ontology files (.owl)
- Python or Python Notebook files

# Getting Started

Download all files and move them to the same folder for easier usage. You might choose between the notebook version (.ipynb file) or the Python script version (.py file).

## Setup

To create a Telegram chatbox, check the BotFather section on: https://core.telegram.org/bots

If you chose the notebook version, you may open it on Jupyter Notebook, Google Colab or any other platform.
If you chose the Python script version, you may open it with any text editor, like VS Code or Sublime Text.

After opening the file, you need to configure the chatbot token (variable token) with your own Telegram chatbot. 

token = "" #Insert here your Chatbot token

It's also possible to configure the bot version by changing the ontology file that will be loaded by the function get_ontology()

onto = get_ontology("mikusec-tsundere.owl") # mikusec-padrao.owl OR mikusec-agressividade.owl OR mikusec-tsundere.owl

That’s it for the setup!

## Talking to the Chatbot

First you need to run one of the files.
You may run the Python script with the command:

python MikuSec.py

For the notebook version, don’t forget to run all cells before the last one, which is a loop.

On Telegram, start a conversation with your chatbot and check if your project idea needs blockchain or not. 
