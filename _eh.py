"""PytSite Assetman Plugin Events Handlers
"""
from pytsite import lang as _lang
from . import _api

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


def plugman_install(name: str, version: str):
    plugin_package_name = 'plugins.' + name

    # Compile plugin's assets
    if _api.is_package_registered(plugin_package_name):
        _api.build(plugin_package_name)

    # Rebuild translations
    if _lang.is_package_registered(plugin_package_name):
        _api.build_translations()
