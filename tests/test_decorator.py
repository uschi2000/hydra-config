import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from hydra_config.decorator import hydra_main2, Token


@dataclass(frozen=True)
class RemoteDataset:
    url: str
    token: Token


@dataclass(frozen=True)
class LocalDataset:
    path: Path


InputTypes = RemoteDataset | LocalDataset
InputConfigurations = dict[str, InputTypes]


@dataclass(frozen=True)
class Config:
    name: str
    answer: int
    tags: list[str]
    inputs: InputConfigurations


def test_decorator_parses_config() -> None:
    # hydra reads command line arguments as config overrides, so we need
    # to remove the pytest arguments in order to not confuse hydra.
    sys.argv = sys.argv[:1]

    @hydra_main2(config_path=Path(__file__).parent / "config")
    def main(config: Config) -> None:
        assert config.name == "foo"
        assert config.answer == 42
        assert config.tags == ["a", "b"]
        assert isinstance(config.tags, list)

        assert config.inputs["default_local_dataset"] == LocalDataset(Path("/data"))
        assert config.inputs["default_remote_dataset"] == RemoteDataset(
            "https://foo/bar",
            Token(UUID("7a72f169-f8c3-4b3e-8041-021a62a2d87f"), "my_token"),
        )
        assert config.inputs["extra_local_dataset"] == LocalDataset(Path("/data_extra"))

    main()
