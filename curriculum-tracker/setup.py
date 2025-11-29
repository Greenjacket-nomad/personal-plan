from setuptools import setup

setup(
    name="curriculum-tracker",
    version="1.0.0",
    py_modules=["track"],
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "track=track:main",
        ],
    },
    python_requires=">=3.10",
    author="Your Name",
    description="CLI tool for tracking curriculum progress",
)
