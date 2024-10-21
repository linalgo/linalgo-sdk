from setuptools import setup, find_packages

setup(
    name='linalgo',
    packages=find_packages(),
    description=(
        'Python library for Natural Language Processing supporting '
        'the open annotation standard'
    ),
    version='0.1',
    author='Arnaud Rachez',
    author_email='arnaud@linalgo.com',
    requires=['numpy', 'scipy', 'pillow'],
)
