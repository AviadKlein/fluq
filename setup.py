from setuptools import setup, find_packages

def __read_version():
    with open('__version__.txt') as f:
        return f.read().strip()
    
def __validate_version_is_aligned_with_toml():
    import re
    toml_version = None
    with open('pyproject.toml') as f:
        for line in f.readlines():
            m = re.match('''^version = "([0-9\.]+)"''', line)
            match m:
                case None:
                    pass
                case _:
                    if len(m.groups()) == 0:
                        raise Exception("matched 0 versions... check the pyproject.toml file")
                    elif len(m.groups()) == 1:
                        toml_version = m.groups()[0]
                    else:
                        raise Exception("matched multiple versions... check the pyproject.toml file")
    if toml_version is None:
        raise Exception("found no 'version' entry in the pyproject.toml file")
    pkg_version = __read_version()
    assert toml_version == pkg_version, f"pyproject.toml version does not match __version__.txt, got {toml_version=} and {pkg_version=}"


__validate_version_is_aligned_with_toml()
__version__ = __read_version()
del(__read_version)

setup(
    name="fluq",  
    version=__version__,
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