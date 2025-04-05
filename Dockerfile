# Usa uma imagem base do Python
FROM python:3.12

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos e o app.py para o contêiner
COPY requirements.txt ./

# Instala as dependências
RUN pip install -r requirements.txt

COPY . .
