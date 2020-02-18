import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="multiquery",
    packages=setuptools.find_packages(),
    install_requires=["psutil", "coloredlogs"],
    entry_points={
        "console_scripts": [
            "multiquery = multiquery.multiquery:main",
            "multiupdate = multiquery.multiupdate:main",
        ],
    },
    version="0.0.1",
    author="Agustin Gianni",
    author_email="agustingianni@gmail.com",
    description="Run a single query on multiple CodeQL databases.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agustingianni/multi-query",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    keywords="codeql"
)
