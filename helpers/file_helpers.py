import yaml
from pathlib import Path


def load_yaml(filename: str) -> dict:
    """
    Функция для загрузки yaml файлов для сравнения.
    __file__ указывает путь до этого файла
    parent - подняться на уровень выше
    """
    path = Path(__file__).parent.parent / "schemas" / filename  # строим путь до файлов yaml
    with path.open(encoding="utf-8") as file:  # открываем файл
        return yaml.safe_load(file)
