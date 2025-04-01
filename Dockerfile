# Usa uma imagem base do Python
FROM python:3.12

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos e o app.py para o contêiner
COPY requirements.txt .

# Instala as dependências
RUN pip install -r requirements.txt

RUN apt-get update
RUN apt-get install -y wget
RUN wget -q


# Expõe a porta 8000 para acessar a aplicação
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["python", "app.py"]
