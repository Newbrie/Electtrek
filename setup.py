from setuptools import setup, find_packages

VERSION = '0.3'
DESCRIPTION = 'Canvassing Package'
LONG_DESCRIPTION = 'Enables the collection , normalisation,  rendering and colelction of electoral data '

# Setting up
setup(
       # the name must match the folder name 'verysimplemodule'
        name="electtrek",
        version=0.3,
        license='Apache 2',
        author="Malcolm Newbury",
        author_email="<malcolm.newbury@guildfoss.com>",
        description="Canvassing Package",
        long_description="Application that enables the Enables the collection , normalisation,  rendering and colelction of electoral data",
        packages=find_packages(),
        install_requires=[], # add any additional packages that
        # needs to be installed along with your package. Eg: 'caer'

        keywords=['python', 'canvassing'],
        classifiers= [
            "Development Status :: 3 - Beta",
            "Intended Audience :: Democracy",
            "Programming Language :: Python :: 3",
            "Operating System :: MacOS :: MacOS X",
        ]
)
