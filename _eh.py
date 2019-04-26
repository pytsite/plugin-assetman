"""PytSite Assetman Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from os import path as _path
from pytsite import plugman as _plugman, reg as _reg, semver as _semver
from . import _api


def on_plugman_pre_install(name: str, version: _semver.Version):
    pkg_name = _plugman.plugin_package_name(name)
    if _api.is_package_registered(pkg_name):
        _api.install_npm_deps(pkg_name)
        _api.build(pkg_name)


def on_plugman_pre_load(name: str):
    # Automatically register plugins packages
    if _path.isdir(_path.join(_plugman.plugin_path(name), 'res', 'assets')):
        _api.register_package(_plugman.plugin_package_name(name))


def on_app_load():
    # Automatically register app's package
    if _path.isdir(_path.join(_reg.get('paths.app'), 'res', 'assets')):
        _api.register_package('app')
