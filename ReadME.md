# Bot de Agendamento de Consultas Médicas via Telegram

Neste ReadME, explico como criei um Bot de Agendamento de Consultas Médicas via Telegram adaptando o código do repositório sugerido no enunciado da Ponderada de Programação da Semana 05 (https://github.com/vthayashi/mikusec).

## 1. Motivação e visão geral

Quando comecei este trabalho, percebi que o código do MikuSec estava voltado para perguntas sobre blockchain. Minha meta era reaproveitar a estrutura básica do bot (conexão com a API do Telegram e lógica de estados) para criar um assistente que coletasse informações de pacientes.

Decidi que o bot deveria solicitar, em ordem, os seguintes dados:

·       Nome completo

·       Data de nascimento

·       CPF

·       RG

·       Endereço

·       Plano de saúde

Após reunir todas essas informações, eu queria que o bot registrasse os dados em uma estrutura organizada (a ontologia) e enviasse uma mensagem de confirmação ao paciente.

## 2. Criando o bot no Telegram

A primeira etapa antes de criar o Notebook foi criar o bot no Telegram. Segui o tutorial e abri uma conversa com o [@BotFather](https://t.me/BotFather), enviei/newbot` e criei a Chave de API.

## 3. Preparando o ambiente no Colab

### 3.1 Instalando dependências

Usei o ChatGPT para a recomendação da biblioteca owlready2, que me permite criar e manipular ontologias em Python.

!pip -q install owlready2

### 3.2 Definindo a ontologia dos pacientes

Para guardar os dados do paciente, criamos uma ontologia chamada **clinic.owl** (Sugerido pelo ChatGPT). 
Definição de Ontologia: Uma ontologia é um modelo formal que define _classes_ (tipos de objetos) e _propriedades_ (atributos e relações) de um domínio específico. (ChatGPT)

Utilizando owlready2, criamos uma classe Paciente e as propriedades de dados do Paciente que iremos armazenar (nome, dataNascimento, cpf, rg, endereco e planoSaude) ligadas a essa classe. Na célula do notebook, o código ficou assim:
```
from owlready2 import *  
onto = get_ontology("http://example.org/clinic.owl")  

with onto:  
    class Paciente(Thing):  
        pass  
    class nome(DataProperty):  
        domain = [Paciente]  
        range = [str]  
    # ... definição das outras propriedades ...  
  
onto.save(file="clinic.owl")
```
(Copiado do Código do Notebook)

Ao salvar a ontologia em arquivo, podemos reutilizá‑la para criar instâncias de pacientes conforme o bot fosse coletando dados.

### 3.3 Configurando o token e estruturas de dados

Importamos as bibliotecas padrão (json, requests, time, urllib), carregamos a ontologia e definimos o nosso TOKEN com a string fornecida pelo BotFather. Se o token estiver vazio, o código lança um erro – isso evita que esqueçamos de configurá‑lo.

Também usamos dois dicionários (Lógica que peguei de uma mistura entre ChatGPT e o código do MikuSec):

·       estado: associa cada chat do Telegram a um número que representa em qual etapa do diálogo o usuário está.

·       paciente_info: armazena temporariamente as respostas de cada usuário até todas as informações serem coletadas.

## 4. Construindo a lógica da conversa

A lógica do bot é baseada em uma **máquina de estados**. Cada número de estado corresponde a uma pergunta ou ação. Quando o bot recebe uma nova mensagem, ele verifica qual estado o usuário está e decide o que fazer. Os dados ficam classificados assim:

|Estado|O que eu faço|Próximo estado|
|---|---|---|
|**0**|Saúdo o usuário e pergunto o nome.|1|
|**1**|Guardo o nome e pergunto a data de nascimento.|2|
|**2**|Guardo a data e pergunto o CPF.|3|
|**3**|Guardo o CPF e pergunto o RG.|4|
|**4**|Guardo o RG e pergunto o endereço.|5|
|**5**|Guardo o endereço e pergunto o plano de saúde.|6|
|**6**|Guardo o plano, crio um indivíduo Paciente na ontologia com todas as informações e envio o resumo.|-1|
|**-1**|Informo que os dados já foram registrados e encerro a conversa.|-1|

Após o estado **6**, o bot cria um novo objeto Paciente na ontologia e insere em cada propriedade os dados coletados.
```
with onto:    p = Paciente()  
    p.nome = [paciente_info[chat_id]['nome']]  
    p.dataNascimento = [paciente_info[chat_id]['dataNascimento']]  
    # ... e assim por diante ...  
onto.save(file='clinic.owl')
```
(Copiado do Código do Notebook)
Em seguida, o bot manda uma mensagem de agradecimento utilizando as informações guardadas e define o estado como -1 para marcar que aquele usuário já concluiu a coleta.

## 5. Polling x Webhooks

No final do notebook, escrevi um LOOP que consulta a API do Telegram a cada segundo por meio da função getUpdates e passa as mensagens novas para process_updates. 
Assim, utilizamos polling para manter o bot ativo e respondendo (apesar de que Webhooks seriam uma melhor abordagem).


---