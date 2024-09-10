from setuptools import setup, find_packages


setup(
    name='uccli',  # This can remain hyphenated
    version='0.0.5',
    packages=find_packages(exclude=['tests', 'concepts', 'state_machine_visualizations']),  # Use find_packages instead
    py_modules=['main'],  # This includes main.py at the root level
    install_requires=[
        'cmd2>=2.0.0',
        'prompt_toolkit>=3.0.0',
        'typing-extensions>=4.0.0',
        'graphviz',
        'tabulate'
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-asyncio>=0.14.0'
        ]
    },
    author='Rene Luijk',
    author_email='rene.luijk@clic2connect.nl',
    description='A small flexible CLI framework with state machine capabilities',
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)