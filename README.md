# Golden Raspberry API

## Descrição

Este projeto consiste em uma API RESTful desenvolvida com **FastAPI** que permite consultar os intervalos entre prêmios consecutivos dos vencedores da categoria **Pior Filme** do **Golden Raspberry Awards**.

A API lê um arquivo CSV contendo os filmes indicados e vencedores, armazenando os dados em um banco de dados **SQLite em memória**. Ao iniciar a aplicação, os dados do arquivo `Movielist.csv` são carregados automaticamente. Além disso, a API disponibiliza um endpoint para upload de novos arquivos CSV, com validação do cabeçalho, independentemente do delimitador utilizado.

## Tecnologias Utilizadas

- **Python** (FastAPI, SQLAlchemy)
- **SQLite** (banco de dados em memória)
- **pytest** (testes de integração)
- **Uvicorn** (servidor ASGI)

## Como Executar o Projeto

### 1. Clonar o repositório

```bash
git clone https://github.com/marc-queiroz/golden-raspberry-api.git
cd golden-raspberry-api
```

### 2. Criar um ambiente virtual e instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Executar a API

```bash
uvicorn main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`.

## Endpoints Disponíveis

### `GET /awards/intervals`

Retorna os produtores com o **menor** e o **maior** intervalo entre prêmios consecutivos.

Exemplo de acesso usando curl:

```bash
curl -X GET "http://127.0.0.1:8000/awards/intervals" -H "accept: application/json"
```

**Exemplo de resposta:**

```json
{
  "min": [
    {
      "producer": "Producer 1",
      "interval": 1,
      "previousWin": 2008,
      "followingWin": 2009
    }
  ],
  "max": [
    {
      "producer": "Producer 2",
      "interval": 99,
      "previousWin": 1900,
      "followingWin": 1999
    }
  ]
}
```

### `POST /upload-csv/`

Endpoint para upload de um arquivo CSV que permite atualizar os dados da base.
**Observação:** O arquivo CSV deve conter as seguintes colunas (no cabeçalho), independentemente do delimitador utilizado:

```
year;title;studios;producers;winner
```

Exemplo de acesso usando curl:

```bash
curl -X POST "http://127.0.0.1:8000/upload-csv/" \
  -H "accept: application/json" \
  -F "file=@caminho/para/seu/arquivo.csv"
```

## Como Rodar os Testes de Integração

```bash
pytest test_main.py
```

Isso garantirá que os endpoints da API estejam funcionando corretamente com base nos dados do CSV.

## Estrutura do Projeto

```
.
├── main.py           # Código principal da API
├── test_main.py      # Testes de integração
├── requirements.txt  # Dependências do projeto
├── README.md         # Documentação do projeto
├── Movielist.csv     # Arquivo CSV de exemplo com os dados dos filmes
```

## Autor

Desenvolvido por **Marc Queiroz** 🚀
