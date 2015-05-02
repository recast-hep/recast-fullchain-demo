from setuptools import setup, find_packages

setup(
  name = 'recast-fullchain-demo',
  version = '0.0.1',
  description = 'recast-dmhiggs-demo',
  url = 'http://github.com/recast-hep/recast-fullchain-demo',
  author = 'Lukas Heinrich',
  author_email = 'lukas.heinrich@cern.ch',
  packages = find_packages(),
  include_package_data = True,
  entry_points = {
      'console_scripts': ['recastworkflow-fullchain=recastfullchain.fullchaincli:fullchaincli'],
  },
  install_requires = [
      'Flask',
      'click',
      'adage',
      'mcviz',
      'reportlab',
      'svg2rlg'
    ],
  dependency_links = [
    'https://github.com/lukasheinrich/mcviz/tarball/master#egg=mcviz-0.1'
  ]
)
