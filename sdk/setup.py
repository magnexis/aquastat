from setuptools import find_packages, setup


setup(
    name="aquastat-sdk",
    version="1.0.1",
    packages=find_packages(),
    install_requires=["httpx>=0.28.1"],
    author="AquaStat Open Source Initiative",
    description="A Python SDK to evaluate and schedule water-aware cloud computing workloads.",
)
