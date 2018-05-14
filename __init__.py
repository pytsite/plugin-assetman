"""PytSite Asset Manager Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Public API
from . import _error as error
from ._api import register_package, library, preload, remove, dump_js, dump_css, url, add_inline, dump_inline, \
    get_urls, get_locations, reset, detect_collection, build, build_translations, build_all, \
    is_package_registered, register_global, t_browserify, t_copy, t_copy_static, t_less, t_js, t_css, js_module, \
    get_src_dir_path, get_dst_dir_path, npm_update, on_split_location


def plugin_load():
    from os import path
    from pytsite import lang, tpl, reg, update

    lang.register_package(__name__)
    tpl.register_package(__name__)

    reg.put('paths.assets', path.join(reg.get('paths.static'), 'assets'))

    _api.register_package(__name__)
    _api.js_module('assetman-build-timestamps', __name__ + '@build-timestamps')
    _api.js_module('assetman-package-aliases', __name__ + '@package-aliases')
    _api.js_module('pytsite-lang-translations', __name__ + '@lang-translations')
    _api.js_module('assetman', __name__ + '@assetman')
    _api.js_module('lang', __name__ + '@lang')
    _api.t_js(__name__)

    # Events handlers
    update.on_update_stage_1(npm_update)


def plugin_load_console():
    from pytsite import console
    from . import _cc

    console.register_command(_cc.Build())


def plugin_load_uwsgi():
    from pytsite import router, tpl

    tpl.register_global('asset_url', url)
    tpl.register_global('css_links', dump_css)
    tpl.register_global('js_links', dump_js)
    tpl.register_global('js_head_links', lambda: dump_js(head=True))
    tpl.register_global('inline_js', dump_inline)

    router.on_dispatch(reset, -999, '*')
    router.on_xhr_dispatch(reset, -999, '*')

    preload(__name__ + '@require.js', True, head=True)
    preload(__name__ + '@require-config.js', True, head=True)


def plugin_install():
    from . import _api

    if not _api.check_setup():
        _api.setup()

    _api.build(__name__)
