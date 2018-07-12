from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    long_description = f.read()

tests_require = [
    'pytest',
    'pytest-runner',
    'coverage',
]

extras_require = {
    'test': tests_require,
}

setup(
    name='Python CAN Viewer',
    url='https://github.com/Lauszus/python_can_viewer',
    description='A simple CAN viewer terminal application written in Python',
    long_description=long_description,
    version='0.0.1',
    packages=find_packages(),
    author='Kristian Sloth Lauszus',
    author_email='lauszus@gmail.com',
    license="GPLv2",
    include_package_data=True,
    zip_safe=False,
    install_requires=['python-can', 'six', 'typing'],
    extras_require=extras_require,
    tests_require=tests_require,
)
