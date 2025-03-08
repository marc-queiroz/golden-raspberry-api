import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app, Base, Movie, get_db
import csv

# Cria o banco SQLite em memória persistente para testes
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def test_client():
    # Configura o banco antes dos testes
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        with open("./Movielist.csv", encoding="utf-8") as file:
            content = file.read()
            lines = content.splitlines()

            # Verifica se o arquivo está vazio
            if not lines:
                pytest.fail("Arquivo CSV vazio. Nenhum dado carregado.")

            # Validação do cabeçalho
            header_line = lines[0].strip()
            expected_header = "year;title;studios;producers;winner"
            if header_line != expected_header:
                pytest.fail(
                    f"Cabeçalho inválido. Esperado: '{expected_header}', encontrado: '{header_line}'"
                )

            reader = csv.DictReader(lines, delimiter=";")

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
                    db.add(movie)
                except Exception as e:
                    db.rollback()
                    pytest.fail(f"Erro na linha {row}: {str(e)}")

            db.commit()

    except FileNotFoundError:
        pytest.fail("Arquivo Movielist.csv não encontrado.")
    except Exception as e:
        db.rollback()
        pytest.fail(f"Falha ao carregar CSV: {str(e)}")
    finally:
        db.close()

    with TestClient(app) as client:
        yield client

    # Limpa o banco após os testes
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Sessão de banco isolada para testes específicos"""
    session = TestingSessionLocal()
    yield session
    session.close()


def test_award_intervals_status_code(test_client):
    response = test_client.get("/awards/intervals")
    assert response.status_code == 200


def test_award_intervals_structure(test_client):
    response = test_client.get("/awards/intervals")
    data = response.json()

    assert "min" in data
    assert "max" in data

    for interval in data["min"]:
        assert "producer" in interval
        assert "interval" in interval
        assert "previousWin" in interval
        assert "followingWin" in interval

    for interval in data["max"]:
        assert "producer" in interval
        assert "interval" in interval
        assert "previousWin" in interval
        assert "followingWin" in interval


def test_award_intervals_logic(test_client):
    response = test_client.get("/awards/intervals")
    data = response.json()

    assert data["min"][0]["interval"] <= data["max"][0]["interval"]


def test_award_intervals_multiple_min_intervals(test_client):
    response = test_client.get("/awards/intervals")
    data = response.json()

    min_intervals = data["min"]
    assert len(min_intervals) >= 1
    min_interval_value = min(i["interval"] for i in data["min"])

    for interval in data["min"]:
        assert interval["interval"] == min_interval_value


def test_award_intervals_multiple_max_intervals(test_client):
    response = test_client.get("/awards/intervals")
    data = response.json()
    max_interval = max(i["interval"] for i in data["max"])

    assert all(i["interval"] == max_interval for i in data["max"])


def test_award_intervals_no_multiple_awards(test_client):
    # Cria banco de teste isolado
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine)

    # Cria tabelas e carrega dados de teste
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Adiciona apenas um filme vencedor
    db.add(
        Movie(
            year=2021,
            title="Single Winner",
            studios="Studio Test",
            producers="Producer Test",
            winner="yes",
        )
    )
    db.commit()

    # Sobrescreve a dependência get_db
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()

    # Executa o teste
    response = test_client.get("/awards/intervals")
    assert response.status_code == 404
    assert "Nenhum produtor" in response.json()["detail"]

    # Limpa sobrescrita
    app.dependency_overrides.clear()
    db.close()


def test_multiple_producers_same_interval(test_client):
    # Configuração de dados de teste
    test_data = [
        Movie(year=2000, producers="Producer A, Producer B", winner="yes"),
        Movie(year=2001, producers="Producer A", winner="yes"),
        Movie(year=2001, producers="Producer B", winner="yes"),
        Movie(year=2020, producers="Producer C", winner="yes"),
        Movie(year=2040, producers="Producer C", winner="yes"),
    ]

    # Sobrescreve o banco de dados temporariamente
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    db.add_all(test_data)
    db.commit()
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()

    # Executa a requisição
    response = test_client.get("/awards/intervals")
    data = response.json()

    # Verifica se há dois produtores com intervalo mínimo de 1 ano
    assert len(data["min"]) == 2
    assert all(interval["interval"] == 1 for interval in data["min"])

    # Limpeza
    app.dependency_overrides.clear()
    db.close()


def test_empty_csv(test_client):
    # Cria um banco de dados vazio
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()

    # Executa a requisição
    response = test_client.get("/awards/intervals")
    assert response.status_code == 404
    assert "Nenhum produtor" in response.json()["detail"]

    # Limpeza
    app.dependency_overrides.clear()
