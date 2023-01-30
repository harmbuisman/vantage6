import codecs
import os

from os import path
from setuptools import setup, find_namespace_packages
from pathlib import Path

# get current directory
here = Path(path.abspath(path.dirname(__file__)))
parent_dir = here.parent.absolute()

# get the long description from the README file
with codecs.open(path.join(parent_dir, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, 'vantage6', 'server', '_version.py')
version_ns = {
    '__file__': version_path
}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name='vantage6-server',
    version=version_ns['__version__'],
    description='Vantage6 server',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/vantage6/vantage6',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'appdirs==1.4.4',
        'flask==2.2.2',
        'Flask-RESTful==0.3.9',
        'Flask-Cors==3.0.10',
        'Flask-JWT-Extended==4.4.4',
        'flask-marshmallow==0.14.0',
        'Flask-SocketIO==5.3.2',
        'SQLAlchemy==1.4.46',
        'Flask-Principal==0.4.0',
        'flasgger==0.9.5',
        'schema==0.7.5',
        'bcrypt==4.0.1',
        'questionary==1.10.0',
        'marshmallow==3.19.0',
        'marshmallow-sqlalchemy==0.28.1',
        'iPython==8.9.0',
        'requests==2.28.2',
        'psutil==5.9.4',
        'gevent==22.10.2',
        'Flask-Mail==0.9.1',
        'requests-oauthlib==1.3.1',
        'gevent-websocket==0.10.1',
        'eventlet==0.33.3',
        'kombu==5.2.4',
        'Werkzeug==2.2.2',
        'jinja2==3.1.2',
        'pyotp==2.8.0',
        f'vantage6 == {version_ns["__version__"]}',
        f'vantage6-common == {version_ns["__version__"]}'
    ],
    extras_require={
        'dev': [
            'termcolor==2.2.0',
            'coverage==4.5.4'
        ]
    },
    package_data={
        'vantage6.server': [
            '__build__',
            '_data/**/*.yaml',
            'server_data/*.yaml',
        ],
    },
    entry_points={
        'console_scripts': [
            'vserver-local=vantage6.server.cli.server:cli_server'
        ]
    }
)
