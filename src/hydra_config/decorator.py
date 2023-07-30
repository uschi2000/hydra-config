import functools
import os
from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from typing import Any
from uuid import UUID

import hydra
from databind.core import Context, Converter, ObjectMapper
from databind.json import JsonModule
from omegaconf import DictConfig
from typeapi import ClassTypeHint, TypeHint


@dataclass(frozen=True)
class Token:
    uid: UUID
    key: str

    def __str__(self) -> str:
        return f"{self.uid}:{self.key}"


class TokenConverter(Converter):
    """A databind converter for Token objects."""

    def convert(self, ctx: Context) -> Any:
        if not isinstance(ctx.datatype, ClassTypeHint) or not issubclass(
            ctx.datatype.type, Token
        ):
            raise NotImplementedError

        if ctx.direction.is_serialize():
            return str(ctx.value)
        elif ctx.direction.is_deserialize():
            if isinstance(ctx.value, str):
                parts = ctx.value.split(":")
                return Token(UUID(parts[0]), parts[1])
            raise NotImplementedError
        else:
            raise Exception("Invalid Context direction, this is a bug")


class ConfigParser:
    mapper: ObjectMapper[Any, Any] = ObjectMapper()
    mapper.module.register(TokenConverter())
    mapper.module.register(JsonModule())

    @staticmethod
    def parse(config: DictConfig, type_hint: TypeHint) -> Any:
        """
        Parses the given input (typically a dictionary loaded from OmegaConf.load())
        into a typed configuration object.
        """
        return ConfigParser.mapper.deserialize(config, type_hint)


def hydra_main2(config_path: Path) -> Callable[[Callable[[Any], Any]], Any]:
    """
    An alternative hydra_main decorator that deserializes the OmegaConf object
    using intro a dataclass using the databind library.
    """

    def main_decorator(
        task_function: Callable[[Any], None]
    ) -> Callable[[Any | None], None]:
        @functools.wraps(task_function)
        def hydra_main(raw_config: Any) -> Any:
            # Converts the given DictConfig into a Config object with the type
            # specified by the main method (ie, typically a project-defined `Config`
            # class).
            parameters = signature(task_function).parameters
            if parameters.get("config") is None:
                raise Exception(
                    "@hydra_main2 method must have first parameter "
                    "of the form `config: Config`"
                )

            config_class = parameters["config"].annotation
            config = ConfigParser.parse(raw_config, TypeHint(config_class))
            return task_function(config)

        def decorated_main(_config: Any | None = None) -> Any:
            hydra_decorator = hydra.main(os.fspath(config_path), "config", "1.3")
            return hydra_decorator(hydra_main)()

        return decorated_main

    return main_decorator
