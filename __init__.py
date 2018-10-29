"""PytSite Asset Manager Plugin
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Public API
from . import _error as error
from ._api import register_package, url, inline_js, reset, build, build_translations, build_all, js, css, \
    is_package_registered, assets_src, assets_dst, on_split_location, assets_public_path, npm_install, setup, \
    resolve_package

# Local imports
from pytsite import semver as _semver


def plugin_load():
    from os import path
    from pytsite import reg, plugman, on_app_load
    from . import _eh

    reg.put('paths.assets', path.join(reg.get('paths.static'), 'assets'))
    plugman.on_pre_load(_eh.on_plugman_pre_load)
    on_app_load(_eh.on_app_load)
    _api.register_package(__name__)


def plugin_pre_install():
    from . import _api

    _api.setup()


def plugin_install():
    from . import _api

    _api.build_all()


def plugin_load_console():
    from pytsite import console
    from . import _cc

    console.register_command(_cc.Setup())
    console.register_command(_cc.NpmInstall())
    console.register_command(_cc.Build())


def plugin_load_wsgi():
    from pytsite import router, tpl

    tpl.register_global('asset_url', url)
    tpl.register_global('css', css)
    tpl.register_global('js', js)
    tpl.register_global('inline_js', inline_js)

    router.on_dispatch(reset, -999, '*')
    router.on_xhr_dispatch(reset, -999, '*')


def plugin_update(v_from: _semver.Version):
    if v_from <= '2.4.3':
        # Required NPM packages added/updated
        from ._api import setup
        setup()
