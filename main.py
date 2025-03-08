import csv
import logging

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do banco de dados em memória
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Modelo Movie do banco de dados
class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    title = Column(String, index=True)
    studios = Column(String)
    producers = Column(String)
    winner = Column(String)


# Criar tabelas
Base.metadata.create_all(bind=engine)

# Iniciar FastAPI
app = FastAPI()


# Função para carregar dados do CSV
def load_movies(db: Session):
    try:
        with open("./Movielist.csv", encoding="utf-8") as file:
            # Lê todo o conteúdo do arquivo
            content = file.read()
            lines = content.splitlines()

            # Verifica se o arquivo está vazio
            if not lines:
                logger.warning("Arquivo CSV vazio. Nenhum dado será carregado.")
                return

            # Validação do cabeçalho
            header_line = lines[0].strip()
            expected_header = "year;title;studios;producers;winner"
            if header_line != expected_header:
                raise ValueError(
                    f"Cabeçalho inválido. Esperado: '{expected_header}', encontrado: '{header_line}'"
                )

            reader = csv.DictReader(lines, delimiter=";")

            logger.debug(f"Colunas detectadas: {reader.fieldnames}")

            for row in reader:
                try:
                    movie = Movie(
                        year=int(row.get("year", 0)),
                        title=row.get("title", "").strip(),
                        studios=row.get("studios", "").strip(),
                        producers=row.get("producers", "").strip(),
                        winner=(
                            "yes" if row["winner"].strip().lower() == "yes" else "no"
                        ),
                    )
                    logger.debug(f"Filme inserido: {movie.title} ({movie.year})")
                    db.add(movie)
                except Exception as e:
                    logger.error(f"Erro na linha {row}: {str(e)}")

            db.commit()

    except FileNotFoundError:
        logger.error("Arquivo Movielist.csv não encontrado.")
        raise
    except ValueError as ve:
        logger.error(f"Erro de validação: {str(ve)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Falha crítica ao carregar o CSV: {str(e)}")
        db.rollback()
        raise


# Carregar os dados ao iniciar o servidor
with SessionLocal() as db:
    load_movies(db)


@app.get("/awards/intervals")
def get_award_intervals(db: Session = Depends(get_db)):
    movies = db.query(Movie).filter(Movie.winner == "yes").all()

    db.close()

    producers_awards = {}
    for movie in movies:
        producers = [
            producer.strip()
            for producer in movie.producers.replace(" and ", ",").split(",")
        ]
        for producer in producers:
            if producer not in producers_awards:
                producers_awards[producer] = []
            producers_awards[producer].append(movie.year)

    intervals = []
    for producer, years in producers_awards.items():
        if len(years) < 2:
            continue
        years.sort()
        for i in range(1, len(years)):
            intervals_dict = {
                "producer": producer,
                "interval": years[i] - years[i - 1],
                "previousWin": years[i - 1],
                "followingWin": years[i],
            }
            intervals.append(intervals_dict)

    if not intervals:
        raise HTTPException(
            status_code=404, detail="Nenhum produtor com múltiplos prêmios encontrado."
        )

    min_interval_value = min(interval["interval"] for interval in intervals)
    max_interval = max(intervals, key=lambda x: x["interval"])["interval"]

    min_producers = [
        interval for interval in intervals if interval["interval"] == min_interval_value
    ]
    max_producers = [
        interval for interval in intervals if interval["interval"] == max_interval
    ]

    return {"min": min_producers, "max": max_producers}


@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    decoded = contents.decode("utf-8")
    lines = decoded.splitlines()

    if not lines:
        raise HTTPException(status_code=400, detail="Arquivo CSV vazio.")

    # Detecta o delimitador utilizando o csv.Sniffer
    dialect = csv.Sniffer().sniff(lines[0])

    # Extrai e valida o header
    header_cols = [col.strip() for col in lines[0].split(dialect.delimiter)]
    expected_cols = ["year", "title", "studios", "producers", "winner"]
    if header_cols != expected_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV header inválido. Esperado: {';'.join(expected_cols)}",
        )

    reader = csv.DictReader(lines, delimiter=dialect.delimiter)

    for row in reader:
        db.add(
            Movie(
                year=int(row["year"]),
                title=row["title"],
                studios=row["studios"],
                producers=row["producers"],
                winner="yes" if row["winner"].lower() == "yes" else "no",
            )
        )

    db.commit()
    return {"message": "CSV carregado com sucesso!"}
