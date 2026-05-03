import random
import pytest
import requests
import allure
from http import HTTPStatus
from config.api_config import BASE_URL, LAVKA_URL
from data.api_variables import TRAINER_ID
from helpers.api_helpers import ApiSession
from helpers.file_helpers import load_yaml
from jsonschema import validate
from deepdiff import DeepDiff


# Маркировка allure по сьютам (ставим на классы)
@allure.suite("Тесты ручки /trainers")
class TestTrainers:
    # Маркировка allure по названию тестов (функций)
    @allure.title("Получение тренеров с сортировкой по городу")
    @pytest.mark.smoke
    @pytest.mark.api
    def test__city_fiter__(self, api_session):
        # Маркировка allure по шагам в тесте (опционально)
        with allure.step("Получаем список тренеров из API с фильтром по городу"):
            city_fiter = "краснодар" # Устанавливаем фильтр по городу (пишем с маленькой, так как ответ будем приводить к нижнему регистру)
            response = api_session.get(  # в каждом тесте респонс меняешь на название функции с фикстурой
                BASE_URL + "/trainers",
                params = {"city": city_fiter}  # квери параметры
            )

        with allure.step("Проверяем код ответа"):
            assert response.status_code == HTTPStatus.OK  # проверка на статус код (200)

        with allure.step("Проверка фильтра по городу"):
            body = response.json()
            assert "data" in body  # проверка, что в боди ответа будет дата
            for trainers in body["data"]:
                assert trainers["city"].lower() == city_fiter  # названия городов приводим к нижнему регистру, чтобы тест не падал из-за регистра


    @allure.title("Получение тренеров с сортировкой по ID")
    @pytest.mark.smoke
    @pytest.mark.api
    def test__id_filter__(self,api_session):
        with allure.step("Получаем список тренеров из API с фильтром по ID"):
            response = api_session.get(
                BASE_URL + "/trainers",
                params={"trainer_id": TRAINER_ID}
            )
        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK  # Ожидаем статус 200

        body = response.json()

        with allure.step("Проверяем наличие data в body"):
            assert "data" in body

        with allure.step("Проверяем, что возвращается только 1 тренер"):
            assert len(body["data"]) == 1  # Проверяем, что вернется только один тренер

        with allure.step("Трейнер ID из ответа совпадает с трейнер ID запроса"):
            trainer = body["data"][0]  # ID находится под первым индексом в ответе (data)
            assert trainer["id"] == TRAINER_ID   # Проверяем, что ID тренера совпадает


    @allure.title("Получение тренеров по городу с сортировкой по убыванию уровня")
    @pytest.mark.smoke
    @pytest.mark.api
    def test__get_trainers_by_city_sorted_desc__(self,api_session):
        with allure.step("Получаем список тренеров из API с фильтром по городу и убыванию уровня"):
            city_fiter = "краснодар"
            response = api_session.get(
                BASE_URL + "/trainers",
                params = {"city": city_fiter,
                          "sort": "desc_level"}
            )
        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK  # Ожидаем статус 200

        body = response.json()

        with allure.step("Проверяем наличие data в body"):
            assert "data" in body

        for trainers in body["data"]:
            assert trainers["city"].lower() == city_fiter

        levels = [trainer["level"] for trainer in body["data"]]
        with allure.step("Сравниваем ответ из body c созданным списком"):
            assert levels == sorted(levels, reverse=True)  # сравниваем список из боди с сортированным списком на убывание


@allure.suite("Тесты ручки /pokemons")
class TestPokemons:
    @allure.title("Отправляет всех живых покемонов тренера в нокаут")
    def knockout_pokemons(self, api_session):
        with allure.step("Получаем список живых покемонов"):
            response = api_session.get(
                BASE_URL + "/pokemons",
                params={"trainer_id": TRAINER_ID,
                        "status": "1"}
            )
        alive_pokemons = response.json().get("data", [])

        with allure.step("Нокаутируем всем живых покемонов"):
            for pokemon in alive_pokemons:
                api_session.post(
                    BASE_URL + "/pokemons/knockout",
                    json={"pokemon_id": pokemon["id"]}
                )

    @allure.title("Создание покемона")
    def create_pokemon(self, api_session):
        with allure.step("Создание покемона"):
            response = api_session.post(
                BASE_URL + "/pokemons",
                json={
                    "name": "generate",
                    "photo_id": -1
                }
            )
        pokemon_id = response.json()["id"]
        return pokemon_id


    @allure.title("Изменение имени покемона")
    @pytest.mark.regress
    def test__patch_pokemon__(self, api_session):
        """
        1. Нокаутирует всех живых покемонов
        2. Создаёт нового покемона
        3. Меняет ему имя через PATCH
        4. Проверяет, что имя изменилось
        """
        self.knockout_pokemons(api_session)  # Нокаутируем всех покемонов

        pokemon_id = self.create_pokemon(api_session)  # Создаём нового покемона

        with allure.step("Меняем имя покемона"):
            new_name = "Измененное имя"
            patch_response = api_session.patch(
                BASE_URL + "/pokemons",
                json={
                    "pokemon_id": pokemon_id,
                    "name": new_name
                }
            )

        with allure.step("Проверяем статус код"):
            assert patch_response.status_code == HTTPStatus.OK  # Ожидаем статус 200

        with allure.step("Получаем список живых покемонов тренера"):
            get_response = api_session.get(
                BASE_URL + "/pokemons",
                params={"trainer_id": TRAINER_ID,
                        "status": "1"}
            )

        with allure.step("Проверяем статус код"):
            assert get_response.status_code == HTTPStatus.OK  # Ожидаем статус 200

        with allure.step("Проверяем, что имя изменилось"):
            pokemon = get_response.json().get("data", [])[0]
            assert pokemon["name"] == new_name  # Из списка с одним покемоном берем имя и сравниваем с новым именем


@allure.suite("Тесты ручки /me")
class TestMe:
    @allure.title("Тест на валидный токен")
    def  test__valid_token__(self, api_session):
        with allure.step("Запрос на ручку /me"):
            response = api_session.get(
                BASE_URL + "/me"
            )

        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK

        body = response.json()
        with allure.step("Проверяем, что в статусе success"):
            assert body["status"] == "success"

        with allure.step("проверяем, что ID пришел верный"):
            assert body["data"][0]["id"] == TRAINER_ID


    @allure.title("Тест на невалидный токен")
    @pytest.mark.skip("Скипаем по заданию")
    def test__invalid_token__(self):
        # Так как тест на некорректный токен, то здесь не применяем api_session и в хедерах пишем свой токен
        with allure.step("Запрос на ручку /me"):
            response = requests.get(
                BASE_URL + "/me",
                headers={"trainer_token": "invalid token"}
            )
        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.UNAUTHORIZED  # Ожидаем ошибку 401 - неавторизован


@allure.suite("Тесты ручки /battle")
class TestBattle:
    @allure.title("Тест ручки GET /battle")
    def test__get_battle__(self, api_session):
        with allure.step("Запрос на ручку /battle"):
            response = api_session.get(
                BASE_URL + "/battle"
            )
            body = response.json()

        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK

        template = load_yaml("battle_get.yml")  # загружаем в переменную yaml из папки schemas
        with allure.step("Сравниваем ответ со схемой"):
            validate(body, template)  # Метод импортируется из jsonschema и сравнивает ответ и yaml. BODY ВСЕГДА ПИШИ ПЕРВЫМ!


@allure.suite("Тесты ручки /achievements")
class TestAchievements:
    @allure.title("Тест ручки GET /achievements")
    def test__get_achievements__(self, api_session):
        with allure.step("Запрос на ручку /battle"):
            response = api_session.get(
                BASE_URL + "/achievements"
            )
            body = response.json()

        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK

        with allure.step("Проверяем боди через DeepDiff"):
            template = load_yaml("achievements_get.yml")  # помещаем yaml в переменную
            validate(body, template)  # сравниваем с yaml файлом
            model = {
                'data': [
                    {'is_reached': False, 'slug': 'beginning'},
                    {'is_reached': False, 'slug': 'out_of_battles'},
                    {'is_reached': False, 'slug': 'self_knockout'},
                    {'is_reached': False, 'slug': 'max_level'},
                    {'is_reached': False, 'slug': 'one_vs_seven'},
                    {'is_reached': False, 'slug': 'five_battles'},
                    {'is_reached': False, 'slug': 'three_defends'}
                ]
            }
            compare = DeepDiff(
                model, body,  # сравнивает построчно body и model
                exclude_regex_paths=[
                    r"root\['data'\]\[\d+\]\['is_reached'\]",  # Пишем путь до ключей, которые нужно игнорировать. [\d+\] - все индексы
                ]
            )
            assert not compare, compare  # При отсутствии ошибок будет пустой словарь и тест упадет. Мы инвертируем проверку


    @allure.title("Тест ручки GET /achievements с неверным параметром is_reached")
    def test__get_achievements_incorrect_is_reached__(self, api_session, check):
        with allure.step("Запрос GET /achievements"):
            response = api_session.get(
                BASE_URL + "/achievements",
                params={"trainer_id": TRAINER_ID,
                        "is_reached": "True"}  # в независимости от того, будет тут строка или булево - ответ сервера будет 500
            )
            body = response.json()

        with allure.step("Проверка статус кода через check"):
            with check:
                assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT  # тест будет падать из-за 500

        with allure.step("Проверка body на наличие сообщения 'Произошла ошибка' через check"):
            with check:
                assert body ['detail']['message'] == 'Произошла ошибка'


@allure.suite("E2E битва покемонов")
class TestE2EBattle:
    @allure.title("Битва покемонов: успешное прохождение")
    def test__run_battle_successfully__(self, api_session: ApiSession, prepare_and_clear_battle: str):
        with allure.step("Находим соперника"):
            ready_for_battle_response = api_session.get(
                BASE_URL + "/pokemons",
                params={"in_pokeball": 1}
            )
            assert ready_for_battle_response.status_code == HTTPStatus.OK
            body = ready_for_battle_response.json()
            suitable_pokemons = [x for x in body["data"] if x ["trainer_id"] != TRAINER_ID]
            enemy_pokemon_id = suitable_pokemons[0]["id"]

            # Генератор. Берет первый попавшийся ID и не перебирает весь список
            # enemy_pokemon_id = next(x for x in body["data"] if x ["trainer_id"] != TRAINER_ID)

        with allure.step("Проводим битву"):
            battle_response = api_session.post(
                BASE_URL + "/battle",
                json={
                    "attacking_pokemon": prepare_and_clear_battle,
                    "defending_pokemon": enemy_pokemon_id
                }
            )
            body = battle_response.json()
            assert battle_response.status_code == HTTPStatus.OK
            assert body["message"] == "Битва проведена"


@allure.suite("E2E покупка премиума")
class TestBuyPremium:
    def create_premium_payment_data(self, cvv: str = "125", days: int = None):
        """Создает словарь для оплаты премиума
        cvv:
            125 - успешная оплата
            300 - недостаточно средств
            555 - ошибка оплаты
        """
        if days is None:
            days = random.randint(1, 999)

        payment_data = {
            "order_type": "premium",
            "details": {
                "days": days,
                "card_number": "5555555544444442",
                "card_name": "german dolnikov",
                "card_actual": "10/27",
                "card_cvv": cvv,
                "secure_code": "56456"
            }
        }
        return payment_data


    @allure.title("Успешная покупка премиума")
    def test__buy_premium__(self, api_session: ApiSession, cancel_premium):
        with allure.step("Покупка премиума"):
            response = api_session.post(
                LAVKA_URL + "/payments",
                json=self.create_premium_payment_data()
            )
        body = response.json()
        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.OK
        with allure.step("Проверяем, что body содержит фразу 'Транзакция успешна'"):
            assert body ["message"] == "Транзакция успешна"


    @pytest.mark.parametrize("cvv,test_name", [
        ("300", "No money in card"),
        ("555", "Incorrect CVV")
    ])
    @allure.title("Покупка премиума с параметризированными некорректными данными (нет денег и неверный cvv")
    def test__buy_premium_negative__(self, api_session: ApiSession, cancel_premium, cvv, test_name):
        with allure.step("Покупка премиума"):
            response = api_session.post(
                LAVKA_URL + "/payments",
                json=self.create_premium_payment_data(cvv=cvv)
            )
        body = response.json()
        with allure.step("Проверяем статус код"):
            assert response.status_code == HTTPStatus.BAD_REQUEST
        with allure.step("Проверяем статус error"):
            assert body["status"] == "error"
