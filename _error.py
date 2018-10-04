"""PytSite Assetman Plugin Errors
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


class PackageNotRegistered(Exception):
    def __init__(self, package_name: str):
        self._package_name = package_name

    def __str__(self):
        return "Assetman package '{}' is not registered".format(self._package_name)


class PackageAlreadyRegistered(Exception):
    def __init__(self, package_name: str):
        self._package_name = package_name

    def __str__(self):
        return "Assetman package '{}' is already registered".format(self._package_name)
