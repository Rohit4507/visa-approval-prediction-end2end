from setuptools import setup, find_packages

__version__ = "0.1.0"

REPO_URL = "https://github.com/Rohit4507/visa-approval-prediction-end2end"

setup(
    name="us_visa",
    version=__version__,
    author="Rohit Singh Rajput",
    author_email="rohitrajput33220@gmail.com",
    description=(
        "End-to-end MLOps pipeline that predicts US visa application "
        "approval using MongoDB Atlas, AWS S3, Docker and GitHub Actions."
    ),
    url=REPO_URL,
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    keywords=[
        "machine-learning",
        "mlops",
        "fastapi",
        "aws",
        "docker",
        "cicd",
        "visa-approval-prediction",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
)
