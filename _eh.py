"""PytSite Assetman Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from os import path as _path
from pytsite import plugman as _plugman, reg as _reg
from . import _api


def on_plugman_pre_load(plugin_name: str):
    # Automatically register plugins packages
    if _path.isdir(_path.join(_plugman.plugin_path(plugin_name), 'res', 'assets')):
        _api.register_package(_plugman.plugin_package_name(plugin_name))


def on_app_load():
    # Automatically register app's package
    if _path.isdir(_path.join(_reg.get('paths.app'), 'res', 'assets')):
        _api.register_package('app')
