from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt', 'r') as f:
    requirements = []
    for line in f:
        requirements.append(line.strip())

setup(
    name = 'PyElit',
    version = '0.1.0',
    author = 'Rich Elton',
    author_email = 'richelton14@gmail.com',
    description = 'Extraction of Locations and Issues of a Text',
    long_description = long_description,
    long_description_content_type="text/markdown",
    packages=["pyelit"],
    install_requires=requirements,
    include_package_data=True,
    url="https://github.com/Rickecr/PyElit",
    project_urls = {
        'Código fonte': 'https://github.com/Rickecr/PyElit',
    },
    keywords = 'geoparsing topic modeling',
    license = 'MIT'
)