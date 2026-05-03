# Фикстуры для тестов API
# Напрямую импортировать фикстуры нельзя, для этого есть файл conftest

import allure
import requests
import pytest
import os  # метод вставляет значения из оперативной памяти, которые лежат в .env
from http import HTTPStatus
from config.api_config import BASE_URL, LAVKA_URL
from helpers.api_helpers import ApiSession


@pytest.fixture(scope="session")
def api_token():
    return os.getenv("POKEMONBATTLE_TOKEN")


@pytest.fixture(scope="session")  # scope - переключатель когда должна действовать функция (session - на всю сессию)
def api_session(api_token):  # Создается функция, куда мы кладем авторизационный ключ и с помощью фикстуры активируем ее перед тестами
    with requests.Session() as pokemon_session:
        pokemon_session.headers.update({"trainer_token": api_token})  # токен в .env
        yield ApiSession(pokemon_session)  # Перенаправляем сессию в ApiSession from helpers.api_helpers


@allure.title("Фикстура создания и удаления покемона для битвы")
@pytest.fixture()
def prepare_and_clear_battle(api_session: ApiSession):
    response = api_session.get(
        BASE_URL + "/me",
    )
    body = response.json()["data"][0]
    if pokemon_list := body["pokemons_in_pokeballs"]:
        pokemon_id = pokemon_list[0]["id"]
    else:
        response = api_session.post(
            BASE_URL + "/pokemons",
            json={
                "name": "generate",
                "photo_id": -1
            }
        )
        body = response.json()
        pokemon_id = body["id"]
        response = api_session.post(
            BASE_URL + "/trainers/add_pokeball",
            json={
                "pokemon_id": pokemon_id
            }
        )
        assert response.status_code == HTTPStatus.OK
    yield pokemon_id
    api_session.post(
        BASE_URL + "/pokemons/knockout",
        json={
            "pokemon_id": pokemon_id
        }
    )


@allure.title("Фикстура аннулирования премиума при его наличии")
@pytest.fixture()
def cancel_premium(api_session: ApiSession):
    yield
    response = api_session.get(
        BASE_URL + "/me",
    )
    body = response.json()

    # Делаем запрос в /me и если премиум True, то делаем запрос на ручку /cancel_premium
    if body["data"][0]["is_premium"]:
        api_session.post(
            LAVKA_URL + "/cancel_premium"
        )
