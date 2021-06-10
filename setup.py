import setuptools
from setuptools import find_namespace_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="analytics_mayhem_adobe",
    version="0.0.10",
    author="Konstantinos Papadopoulos",
    author_email="info@analyticsmayhem.com",
    description="Manage Adobe Analytics Reports API v2 requests to build reports programmatically.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/konosp/adobe-analytics-reports-api-v2.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pandas",
        "requests",
        "PyJWT"
    ],
    python_requires='>=3.6',
)