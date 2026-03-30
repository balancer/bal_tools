from setuptools import setup, find_packages

VERSION = "0.1.21"
DESCRIPTION = "Balancer Tools"
LONG_DESCRIPTION = "Balancer Maxi helper and ecosystem tools"

setup(
    name="bal_tools",
    version=VERSION,
    author="jalbrekt85",
    author_email="<nospam@balancer.community>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    include_package_data=True,  # Automatically include non-Python files
    package_data={
        "bal_tools": [
            "abi/*.json",
            "graphql/**/*.gql",
            "safe_tx_builder/templates/*.json",
        ]
    },
    url="https://github.com/balancer/bal_tools",
    install_requires=[
        "wheel",
        "web3>=6.0.0",
        "pathlib>=1.0",
        "numpy==1.26.4",
        "pandas",
        "dotmap",
        "munch==4.0.0",
        "gql[requests]",
        "pydantic",
        "json-fix",
        "lxml",
        "dotenv",
    ],
    extras_require={
        "brownie": [
            "eth-brownie @ git+https://github.com/balancer/brownie.git@v1.20.x"
        ],
    },
    keywords=["python", "first package"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Linux",
    ],
)
