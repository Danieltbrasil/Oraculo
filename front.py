import streamlit as st
import tempfile
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import WebBaseLoader, YoutubeLoader, CSVLoader, TextLoader, PyPDFLoader
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from fake_useragent import UserAgent
import os
from time import sleep

TIPOS_ARQUIVOS_VALIDOS = [
    "Site", "Youtube", "Pdf", "Csv", "Txt"
]

CONFIG_MODELOS = {"Groq": 
                        {"modelos": ["llama-3.3-70b-versatile", "gemma2-9b-it", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
                         "chat": ChatGroq},
                  "OpenAI": 
                        {"modelos": ["gpt-4o-mini", "gpt-4o", "o1-preview", "o1-mini"],
                         "chat": ChatOpenAI}}

def carrega_arquivo(tipo_arquivo, arquivo):
    documento = None
    
    if tipo_arquivo == "Site":
        documento = carrega_site(arquivo)

    if tipo_arquivo == "Youtube":
        documento = carrega_youtube(arquivo)

    if tipo_arquivo == "Pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        documento = carrega_pdf(nome_temp)

    if tipo_arquivo == "Csv":
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        documento = carrega_csv(nome_temp)

    if tipo_arquivo == "Txt":
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        documento = carrega_txt(nome_temp)

    return documento

def carrega_site(url):
    documento = ""
    for i in range(5):
        try:
            os.environ["USER_AGENT"] = UserAgent().random
            loader = WebBaseLoader(url, raise_for_status=True)
            lista_documentos = loader.load()
            documento = "\n".join([doc.page_content for doc in lista_documentos])
            break
        except:
            st.error(f"Deu ruim no site... pela {i}º vez")
            sleep(3)
            
    if documento == "":
        st.error("Fiz o que pude e não consegui... fui mlk, tente outro site ou novamente mais tarde")
        st.stop()
        
    return documento

def carrega_youtube(video_id):
    loader = YoutubeLoader(video_id, add_video_info=False, language=["pt-br"])
    lista_documentos = loader.load()
    documento = "\n".join([doc.page_content for doc in lista_documentos])
    return documento

def carrega_csv(arquivo):
    loader = CSVLoader(arquivo)
    lista_documentos = loader.load()
    documento = "\n".join([doc.page_content for doc in lista_documentos])
    return documento

def carrega_pdf(arquivo):
    loader = PyPDFLoader(arquivo)
    lista_documentos = loader.load()
    documento = "\n".join([doc.page_content for doc in lista_documentos])
    return documento

def carrega_txt(arquivo):
    loader = TextLoader(arquivo)
    lista_documentos = loader.load()
    documento = "\n".join([doc.page_content for doc in lista_documentos])
    return documento


MEMORIA = ConversationBufferMemory()


def carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo):
    documento = carrega_arquivo(tipo_arquivo, arquivo)

    system_message = '''Você é um assistente amigável chamado Oráculo.
    Você possui acesso às seguintes informações vindas 
    de um documento {}: 

    ####
    {}
    ####

    Utilize as informações fornecidas para basear as suas respostas.

    Sempre que houver $ na sua saída, substita por S.

    Se a informação do documento for algo como "Just a moment...Enable JavaScript and cookies to continue" 
    sugira ao usuário carregar novamente o Oráculo!'''.format(tipo_arquivo, documento)

    template = ChatPromptTemplate.from_messages([("system", system_message),
                                                 ("placeholder", "{chat_history}"), 
                                                 ("user", "{input}")])

    chat = CONFIG_MODELOS[provedor]["chat"](model=modelo, api_key=api_key)
    chain = template | chat

    st.session_state["chain"] = chain

def pagina_chat():
    st.header("🤖Bem-vinda ao seu Oráculo Meu docinho", divider=True)

    chain = st.session_state.get("chain")

    if chain is None:
        st.error("Oráculo, eu sou seu pai... Agora carregue ele!")
        st.stop()

    memoria = st.session_state.get("memoria", MEMORIA)
    for mensagem in memoria.buffer_as_messages:
        chat = st.chat_message(mensagem.type)
        chat.markdown(mensagem.content)

    input_usuario = st.chat_input("Abra seu coração")
    if input_usuario:
        chat = st.chat_message("human")
        chat.markdown(input_usuario)

        chat = st.chat_message("ai")
        resposta = chat.write_stream(chain.stream({"input": input_usuario, "chat_history": memoria.buffer_as_messages}))
        
        memoria.chat_memory.add_user_message(input_usuario)
        memoria.chat_memory.add_ai_message(resposta)
        st.session_state["memoria"] = memoria


def sidebar():
    tabs = st.tabs(["Plataforma 9¾", "Escolha seu feitiço"])
    with tabs[0]:
        tipo_arquivo = st.selectbox("Escolha a categoria dessa belezinha", TIPOS_ARQUIVOS_VALIDOS)
        if tipo_arquivo == "Site":
            arquivo = st.text_input("Manda aí o link mágico")

        if tipo_arquivo == "Youtube":
            arquivo = st.text_input("Joga o id do vídeo")

        if tipo_arquivo == "Pdf":
            arquivo = st.file_uploader("Invoque das trevas o arquivo pdf", type=[".pdf"])
        
        if tipo_arquivo == "Csv":
            arquivo = st.file_uploader("Mande seu arquivo para a missão csv", type=[".csv"])
        
        if tipo_arquivo == "Txt":
            arquivo = st.file_uploader("Despeje seu arquivo txt", type=[".txt"])
        
    with tabs[1]:
        provedor = st.selectbox("Obi-Wan ou Han Solo?", CONFIG_MODELOS.keys())
        modelo = st.selectbox("Escolha o mestre", CONFIG_MODELOS[provedor]["modelos"])
        api_key = st.text_input(
            f"Desbloqueie os poderes secretos com a chave {provedor}",
            value=st.session_state.get(f"api_key_{provedor}"))

        st.session_state[f"api_key_{provedor}"] = api_key
    
    if st.button("Chamar o sábio supremo do momo", use_container_width=True):
        if arquivo is None:
            st.error("Alimente-me... preciso consumir dados")
        else:
            carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo)
    if st.button("Sumir com as evidências", use_container_width=True):
        st.session_state["memoria"] = MEMORIA

def main():
    with st.sidebar:
        sidebar()
    pagina_chat()


if __name__ == "__main__":
    main()
