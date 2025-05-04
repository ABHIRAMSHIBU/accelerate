from setuptools import setup, find_packages

setup(
    name="japa",
    version="0.1.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "python-telegram-bot>=20.0",
    ],
    entry_points={
        "console_scripts": [
            "japa=main:main",
        ],
    },
    author="JAPA Team",
    author_email="example@example.com",
    description="JAPA: Just Another Project Automation - A server service monitor with Telegram interface",
    keywords="telegram, monitoring, service",
    python_requires=">=3.7",
) 