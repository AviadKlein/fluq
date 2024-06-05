from setuptools import setup, find_packages

setup(
    name="fluq",  
    version="0.1.1",
    author="Aviad Klein",
    author_email="aviad.klein@gmail.com",
    description="Python style api for heavy SQL writers",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/AviadKlein/fluq",  
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
)