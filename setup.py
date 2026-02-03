from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adp-api-client",
    version="1.0.0",
    author="Joey Russoniello",
    description="A robust client library for ADP Workforce Now API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JoeyRussoniello/API_Clients",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "urllib3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
