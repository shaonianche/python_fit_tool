from setuptools import setup

setup(name='fit-tool',
      version='0.9.14',
      description='A library for reading and writing Garmin FIT files.',
      long_description=open('README.md', 'r').read(),
      long_description_content_type='text/markdown',
      url='https://bitbucket.org/stagescycling/python_fit_tool.git',
      author='Matt Tucker',
      author_email='mtucker@stagescycling.com',
      license='none',
      packages=['fit_tool', 'fit_tool.profile', 'fit_tool.utils', 'fit_tool.profile.messages'],
      install_requires=['openpyxl==2.5.12', 'bitstruct==8.11.1'],
      zip_safe=False,
      test_suite='nose.collector',
      tests_require=['nose'],
      scripts=['bin/fittool'])
