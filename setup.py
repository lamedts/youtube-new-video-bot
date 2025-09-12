from setuptools import setup, find_packages

# Read dependencies from requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="youtube-new-video-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,
    # python_requires=">=3.12,<3.13",  # enforce Python version
    entry_points={
        "console_scripts": [
            "youtube-bot=main:main",  # allows running bot as `youtube-bot`
        ],
    },
)
