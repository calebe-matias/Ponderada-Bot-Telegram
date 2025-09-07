# Bot de Agendamento de Consultas Médicas – Documentação

Esta documentação explica passo a passo como adaptar o bot original do projeto **MikuSec** para que ele funcione como assistente de uma **clínica médica**, coletando dados de pacientes que desejam agendar consultas. O documento também apresenta de forma acessível o conceito de **ontologia** usado no código e como ela é construída com a biblioteca owlready2.

## 1. Visão geral

O bot conversa com o paciente pelo Telegram e solicita, de forma sequencial, os seguintes dados:

·       **Nome completo**

·       **Data de nascimento**

·       **CPF**

·       **RG**

·       **Endereço**

·       **Nome do plano de saúde**

Após coletar essas informações, o bot registra os dados em uma ontologia (arquivo clinic.owl) e responde com um resumo, indicando que a clínica entrará em contato para confirmar a consulta.

## 2. Criação do bot no Telegram

1.       No Telegram, inicie uma conversa com o usuário [@BotFather](https://t.me/BotFather).

2.       Envie o comando /newbot e siga as instruções: escolha um **nome** (ex.: ClinicaBot) e um **username** (terminado em bot).

3.       O BotFather retornará um **token**, uma sequência como 123456789:ABCDE.... **Copie e guarde esse token**, pois ele será usado para autenticar o seu bot na API do Telegram.

## 3. Preparação do ambiente

### 3.1 Instalação de dependências

No Google Colab, abra o notebook bot_clinica_colab.ipynb e execute a primeira célula de código. Ela instala a biblioteca owlready2, que é usada para manipular ontologias em Python.

!pip -q install owlready2

### 3.2 Definição da ontologia

Uma **ontologia** é um modelo estruturado que representa conceitos e relacionamentos de um determinado domínio. No contexto deste bot, a ontologia é usada para representar **pacientes** e os atributos associados a eles (nome, data de nascimento, CPF etc.). Utilizamos a biblioteca owlready2 para criar, manipular e salvar essa ontologia.

No notebook há uma célula que define a ontologia clinic.owl da seguinte forma:

from owlready2 import *  
  
# Cria ou carrega uma ontologia simples  
onto = get_ontology("http://example.org/clinic.owl")  
  
with onto:  
    class Paciente(Thing):  
        pass  
    class nome(DataProperty):  
        domain = [Paciente]  
        range = [str]  
    class dataNascimento(DataProperty):  
        domain = [Paciente]  
        range = [str]  
    class cpf(DataProperty):  
        domain = [Paciente]  
        range = [str]  
    # ... outras propriedades (rg, endereco, planoSaude)  
  
onto.save(file="clinic.owl")

·       Paciente é uma **classe** (tipo de objeto) que representa cada paciente.

·       nome, dataNascimento, cpf, rg, endereco e planoSaude são **propriedades de dados** (DataProperty) associadas à classe Paciente. Elas indicam que um paciente possui um nome (texto), data de nascimento etc. O atributo domain=[Paciente] indica que a propriedade está ligada à classe Paciente, e range=[str] especifica que o valor deve ser uma string.

·       Ao final, a ontologia é salva em um arquivo clinic.owl, permitindo reutilização futura.

Essa ontologia é muito simples, mas ilustra a ideia de modelar informações de forma estruturada e reutilizável.

### 3.3 Configuração do token

Na célula de configuração do notebook, você deve importar as bibliotecas necessárias, carregar a ontologia salva (clinic.owl) e definir o token do seu bot:

from owlready2 import get_ontology  
onto = get_ontology("clinic.owl").load()  
  
TOKEN = 'SEU_TOKEN_AQUI'  # substitua pelo token obtido com o BotFather

A variável URL é montada a partir do token para formar o endereço base das requisições à API do Telegram (ex.: https://api.telegram.org/bot<SEU_TOKEN>/). Dois dicionários são inicializados:

·       **estado**: guarda, para cada usuário, em qual etapa do diálogo (passo) ele se encontra.

·       **paciente_info**: armazena temporariamente as respostas coletadas de cada usuário.

## 4. Lógica da conversa (fluxo de estados)

O bot funciona como uma **máquina de estados**. A cada mensagem enviada pelo usuário, o bot consulta o valor atual de estado[chat_id] e determina qual pergunta fazer ou qual campo deve receber a resposta. O fluxo principal está implementado na função process_updates:

|Estado|Ação do bot|Próximo estado|
|---|---|---|
|**0**|Saudações. Pergunta o nome completo.|1|
|**1**|Armazena o nome e pergunta a data de nascimento.|2|
|**2**|Armazena a data de nascimento e pergunta o CPF.|3|
|**3**|Armazena o CPF e pergunta o RG.|4|
|**4**|Armazena o RG e pergunta o endereço completo.|5|
|**5**|Armazena o endereço e pergunta o plano de saúde.|6|
|**6**|Armazena o plano de saúde, cria um indivíduo Paciente na ontologia com todos os dados, salva a ontologia em clinic.owl e envia um resumo ao usuário.|-1|
|**-1**|Informa que os dados já foram registrados e encerra a conversa (aguarda novas interações).|-1|

### 4.1 Como os dados são armazenados

Quando o bot chega ao passo **6**, ele cria um novo indivíduo da classe Paciente na ontologia:

with onto:    p = Paciente()  
    p.nome = [paciente_info[chat_id]['nome']]  
    p.dataNascimento = [paciente_info[chat_id]['dataNascimento']]  
    p.cpf = [paciente_info[chat_id]['cpf']]  
    p.rg = [paciente_info[chat_id]['rg']]  
    p.endereco = [paciente_info[chat_id]['endereco']]  
    p.planoSaude = [paciente_info[chat_id]['planoSaude']]  
onto.save(file='clinic.owl')

Cada chamada como p.nome = [...] associa o valor coletado à propriedade nome do paciente criado. Depois, onto.save(...) atualiza o arquivo clinic.owl para que os dados sejam persistidos.

### 4.2 Mensagem de confirmação

Após registrar o paciente, o bot monta uma mensagem de resumo utilizando os dados armazenados no dicionário paciente_info[chat_id] e envia ao usuário, agradecendo e avisando que a clínica entrará em contato. O estado do usuário é definido como -1 para indicar que a coleta terminou.

## 5. Loop principal

A última célula do notebook inicia um laço infinito que consulta a API do Telegram a cada segundo através da função get_updates. Se existirem novas mensagens (updates['result']), o offset é atualizado para não reprocessar mensagens antigas e a função process_updates é chamada para tratar cada uma. Esse laço mantém o bot ativo enquanto a célula estiver sendo executada.

## 6. Considerações finais

·       **Privacidade:** O bot coleta dados sensíveis (CPF, RG). Em um cenário real, essas informações devem ser armazenadas de forma segura (criptografia, acesso restrito etc.). O exemplo aqui tem fins educacionais.

·       **Validação:** O código apresentado não valida os formatos de CPF, datas ou outros campos. Para uso profissional, implemente validação de dados e tratamento de erros.

·       **Escalabilidade:** A abordagem utiliza _long polling_ para ler mensagens. Para maior escalabilidade, considere usar _webhooks_ e frameworks dedicados (por exemplo, python-telegram-bot).

·       **Ontologia:** Mesmo sendo simples, a ontologia clinic.owl permite armazenar e consultar pacientes de forma estruturada. Em projetos maiores, ontologias podem representar relações complexas (consultas, médicos, convênios, horários, etc.), facilitando a integração de sistemas e a consistência de dados.

## 7. Como experimentar

1.       **Configure o bot e o token.**

2.       **Execute o notebook no Google Colab.**

3.       **Converse com o seu bot no Telegram.** Ele fará as perguntas na ordem indicada e registrará suas respostas.

4.       **Verifique o arquivo** **clinic.owl**. Faça download ou abra no Colab para ver as instâncias criadas; use owlready2 para inspecionar as propriedades dos pacientes.

Seguindo estes passos e entendendo a lógica de estados e da ontologia, você poderá adaptar o bot para outras aplicações ou expandir o modelo de dados da clínica.

---