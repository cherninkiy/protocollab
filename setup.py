from setuptools import setup, find_packages

setup(
    name="protocollab",
    version="0.0.1",
    packages=find_packages(),  # ищет все пакеты в корне
    install_requires=["ruamel.yaml", "pydantic"],
)