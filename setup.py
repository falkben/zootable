from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("requirements-test.txt") as f:
    testing = f.read().splitlines()

setup(
    name="zootable",
    author="Benjamin Falk",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={"test": testing},
)
