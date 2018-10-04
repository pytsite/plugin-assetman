"""PytSite Asset Manager Plugin
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Public API
from . import _error as error
from ._api import register_package, preload, js_tags, css_tags, url, add_inline_js, inline_js, reset, build, \
    build_translations, build_all, is_package_registered, assets_src, assets_dst, on_split_location, js_tag, css_tag

from pytsite import semver as _semver


def plugin_load():
    from os import path
    from pytsite import reg, plugman
    from . import _eh

    reg.put('paths.assets', path.join(reg.get('paths.static'), 'assets'))
    plugman.on_pre_load(_eh.on_plugman_pre_load)
    _api.register_package(__name__)


def plugin_pre_install():
    from . import _api

    _api.setup()


def plugin_install():
    from . import _api

    _api.build(__name__)


def plugin_load_console():
    from pytsite import console
    from . import _cc

    console.register_command(_cc.Setup())
    console.register_command(_cc.NpmInstall())
    console.register_command(_cc.Build())


def plugin_load_wsgi():
    from pytsite import router, tpl

    tpl.register_global('asset_url', url)
    tpl.register_global('css_tag', css_tag)
    tpl.register_global('css_tags', css_tags)
    tpl.register_global('js_tag', js_tag)
    tpl.register_global('js_tags', js_tags)
    tpl.register_global('js_head_tags', lambda: js_tags(head=True))
    tpl.register_global('inline_js', inline_js)

    router.on_dispatch(reset, -999, '*')
    router.on_xhr_dispatch(reset, -999, '*')


def plugin_update(v_from: _semver.Version):
    if v_from <= '2.4.3':
        # Required NPM packages added/updated
        from ._api import setup
        setup()
