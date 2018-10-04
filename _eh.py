"""PytSite Assetman Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from os import path as _path
from pytsite import plugman as _plugman
from . import _api


def on_plugman_pre_load(plugin_name: str):
    res_path = _path.join(_plugman.plugin_path(plugin_name), 'res', 'assets')
    if _path.isdir(res_path):
        _api.register_package(_plugman.plugin_package_name(plugin_name))
