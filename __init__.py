"""PytSite Asset Manager Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import plugman as _plugman

# Public API
if _plugman.is_installed(__name__):
    from . import _error as error
    from ._api import register_package, library, preload, remove, dump_js, dump_css, url, add_inline, dump_inline, \
        get_urls, get_locations, reset, detect_collection, build, build_translations, build_all, \
        is_package_registered, register_global, t_browserify, t_copy, t_copy_static, t_less, t_js, t_css, js_module, \
        get_src_dir_path, get_dst_dir_path, npm_update, on_split_location


def plugin_load():
    from os import path
    from pytsite import reg, lang, tpl, update as pytsite_update
    from . import _api

    reg.put('paths.assets', path.join(reg.get('paths.static'), 'assets'))

    # Resources
    lang.register_package(__name__)
    tpl.register_package(__name__)

    # Event handlers
    pytsite_update.on_update_stage_1(npm_update)
    pytsite_update.on_update_after(build_all)
    pytsite_update.on_update_after(build_translations)

    # Register assetman itself and add required assets for all pages
    register_package(__name__)

    js_module('assetman-build-timestamps', __name__ + '@build-timestamps')
    js_module('pytsite-lang-translations', __name__ + '@lang-translations')
    js_module('assetman', __name__ + '@assetman')
    js_module('lang', __name__ + '@lang')

    t_js(__name__)


def plugin_load_console():
    from pytsite import console
    from . import _console_commands

    console.register_command(_console_commands.Build())


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
    plugin_load()

    from . import _api

    if not _api.check_setup():
        from pytsite import lang

        lang.register_package(__name__)
        _api.setup()

    _api.build_all()
    _api.build_translations()
