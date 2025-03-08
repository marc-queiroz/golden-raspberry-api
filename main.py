from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Boolean, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import csv
import logging

# Configuração básica do logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuração do banco de dados em memória
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Função para carregar dados do CSV
def load_movies():
    db = SessionLocal()
    with open("./Movielist.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")  # Corrigido para ';'
        logger.debug(f"Colunas encontradas: {reader.fieldnames}")

        for row in reader:
            try:
                movie = Movie(
                    year=int(row.get("year", 0)),
                    title=row.get("title", "").strip(),
                    studios=row.get("studios", "").strip(),
                    producers=row.get("producers", "").strip(),
                    winner=(
                        "yes"
                        if row.get("winner", "").strip().lower() == "yes"
                        else "no"
                    ),
                )
                logger.debug(
                    f"Inserindo filme: {movie.title} ({movie.year}) - Vencedor: {movie.winner}"
                )
                db.add(movie)
            except Exception as e:
                logger.error(f"Erro ao inserir filme {row}: {e}")
    db.commit()
    db.close()


# Carregar os dados ao iniciar o servidor
load_movies()


@app.get("/awards/intervals")
def get_award_intervals():
    db = SessionLocal()

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
