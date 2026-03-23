"""
Безопасный конструктор YAML с поддержкой только тега !include.
Блокирует выполнение произвольного Python-кода через опасные теги.
Ограничивает глубину вложенности через встроенную проверку маппингов
и fallback-проверку пост-парсинга (construct_document).
"""

import logging
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import YAMLError

logger = logging.getLogger(__name__)



class RestrictedSafeConstructor(RoundTripConstructor):
    def __init__(self, max_depth=50, base_depth=0, *args, **kwargs):
        if max_depth is None:
            raise ValueError("max_depth cannot be None; set a positive integer")
        if not isinstance(max_depth, int) or max_depth <= 0:
            raise ValueError("max_depth must be a positive integer")
        super().__init__(*args, **kwargs)
        self.max_depth = max_depth
        self._depth = base_depth
        self._base_depth = base_depth
        self._remove_dangerous_constructors()

    def construct_mapping(self, node, maptyp=None, deep=False):
        self._check_and_incr_depth()
        try:
            # Принудительно включаем рекурсивный обход
            return super().construct_mapping(node, maptyp, deep=True)
        finally:
            self._depth -= 1

    def construct_object(self, node, deep=False):
        """
        Только проверка разрешённых тегов, без управления глубиной.
        """
        allowed_tags = {
            'tag:yaml.org,2002:null',
            'tag:yaml.org,2002:bool',
            'tag:yaml.org,2002:int',
            'tag:yaml.org,2002:float',
            'tag:yaml.org,2002:str',
            'tag:yaml.org,2002:binary',
            'tag:yaml.org,2002:timestamp',
            'tag:yaml.org,2002:omap',
            'tag:yaml.org,2002:pairs',
            'tag:yaml.org,2002:set',
            'tag:yaml.org,2002:seq',
            'tag:yaml.org,2002:map',
            '!include',
        }

        if node.tag not in allowed_tags:
            if any(dangerous in str(node.tag) for dangerous in ['python/', '!!python']):
                raise YAMLError(
                    f"Dangerous Python tag '{node.tag}' detected and blocked. "
                    f"This library does not allow arbitrary Python code execution via YAML."
                )
            else:
                raise YAMLError(
                    f"Unknown tag '{node.tag}' detected and blocked. "
                    f"Only standard YAML types and !include are allowed for security reasons."
                )

        return super().construct_object(node, deep)

    def _remove_dangerous_constructors(self):
        """Удаляет потенциально опасные конструкторы."""
        dangerous_prefixes = ['tag:yaml.org,2002:python/', '!!python/']
        to_remove = []
        for tag in self.yaml_constructors:
            if tag is None or not isinstance(tag, str):
                continue
            for prefix in dangerous_prefixes:
                if prefix in tag:
                    to_remove.append(tag)
        for tag in to_remove:
            del self.yaml_constructors[tag]

    def _check_and_incr_depth(self):
        """
        Проверяет и увеличивает текущую глубину вложенности.
        Выбрасывает исключение при превышении лимита.
        """
        self._depth += 1
        if self._depth > self.max_depth:
            self._depth -= 1
            raise ValueError(f"Exceeded maximum nesting depth of {self.max_depth}")

    def _check_structure_depth(self, data, current):
        """
        Рекурсивная проверка глубины структуры после парсинга.
        Используется как fallback для последовательностей, у которых
        проверка во время парсинга может быть подавлена генераторным механизмом.
        """
        if current > self.max_depth:
            raise ValueError(f"Exceeded maximum nesting depth of {self.max_depth}")
        if isinstance(data, dict):
            for v in data.values():
                self._check_structure_depth(v, current + 1)
        elif isinstance(data, list):
            for item in data:
                self._check_structure_depth(item, current + 1)

    def construct_document(self, node):
        """Переопределяем для добавления fallback-проверки глубины после парсинга."""
        result = super().construct_document(node)
        if result is not None:
            self._check_structure_depth(result, self._base_depth)
        return result


def create_safe_yaml_instance(max_depth: int = 50, base_depth: int = 0):
    """
    Создаёт безопасный экземпляр YAML с round-trip preservation,
    поддержкой только тега !include и ограничением глубины вложенности.
    """
    if max_depth is None:
        raise ValueError("max_depth cannot be None; set a positive integer")
    if not isinstance(max_depth, int) or max_depth <= 0:
        raise ValueError("max_depth must be a positive integer")
        
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    def make_constructor(max_depth=max_depth, base_depth=base_depth):
        class CustomConstructor(RestrictedSafeConstructor):
            def __init__(self, *args, **kwargs):
                super().__init__(max_depth=max_depth, base_depth=base_depth, *args, **kwargs)
        return CustomConstructor

    yaml.Constructor = make_constructor(max_depth=max_depth, base_depth=base_depth)
    yaml._make_constructor = make_constructor  # для передачи base_depth при include
    return yaml