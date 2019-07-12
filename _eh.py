"""PytSite Assetman Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from os import path
from semaver import Version
from pytsite import plugman, reg
from . import _api


def on_plugman_pre_install(name: str, version: Version):
    pkg_name = plugman.plugin_package_name(name)
    if _api.is_package_registered(pkg_name):
        _api.install_npm_deps(pkg_name)
        _api.build(pkg_name)


def on_plugman_pre_load(name: str):
    # Automatically register plugins packages
    if path.isdir(path.join(plugman.plugin_path(name), 'res', 'assets')):
        _api.register_package(plugman.plugin_package_name(name))


def on_app_load():
    # Automatically register app's package
    if path.isdir(path.join(reg.get('paths.app'), 'res', 'assets')):
        _api.register_package('app')
