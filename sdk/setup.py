from pathlib import Path

from setuptools import find_packages, setup


README = Path(__file__).with_name("README.md").read_text(encoding="utf-8")


setup(
    name="aquastat-sdk",
    version="1.0.1",
    packages=find_packages(),
    install_requires=["httpx>=0.28.1"],
    author="AquaStat Open Source Initiative",
    description="A Python SDK to evaluate and schedule water-aware cloud computing workloads.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/magnexis/aquastat",
    project_urls={
        "Documentation": "https://aquastat-api.onrender.com/docs",
        "Source": "https://github.com/magnexis/aquastat",
        "Issues": "https://github.com/magnexis/aquastat/issues",
    },
    license="Apache-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
