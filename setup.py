"""Setup script for Crypto Market Analysis SaaS."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crypto-market-analysis-saas",
    version="0.1.0",
    author="Crypto Vision Team",
    description="A comprehensive cryptocurrency market analysis and prediction system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "Flask>=3.0.0",
        "SQLAlchemy>=2.0.23",
        "psycopg2-binary>=2.9.9",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "numpy>=1.26.2",
        "pandas>=2.1.4",
        "scikit-learn>=1.3.2",
        "tensorflow>=2.15.0",
        "streamlit>=1.29.0",
        "plotly>=5.18.0",
        "APScheduler>=3.10.4",
        "openai>=1.6.1",
        "twilio>=8.11.0",
        "boto3>=1.34.10",
        "spacy>=3.7.2",
        "Flask-CORS>=4.0.0",
        "Flask-Limiter>=3.5.0",
        "cryptography>=41.0.7",
        "alembic>=1.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "flake8>=6.1.0",
            "black>=23.12.1",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
