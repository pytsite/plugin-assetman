"""PytSite Assetman Plugin API Functions
"""
import subprocess as _subprocess
import json as _json
from typing import Dict as _Dict, List as _List, Tuple as _Tuple, Union as _Union, Callable as _Callable
from os import path as _path, chdir as _chdir, makedirs as _makedirs, unlink as _unlink, getcwd as _getcwd
from shutil import rmtree as _rmtree
from importlib.util import find_spec as _find_spec
from time import time as _time
from pytsite import router as _router, threading as _threading, util as _util, reg as _reg, console as _console, \
    lang as _lang, tpl as _tpl, events as _events, logger as _logger
from . import _error

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

_package_paths = {}  # type: _Dict[str, _Tuple[str, str]]
_package_aliases = {}  # type: _Dict[str, str]
_libraries = {}  # type: _Dict[str, _Union[_List, _Callable[..., _List]]]

_tasks = []  # type: _List[_Tuple]
_requirejs_modules = {}  # type: _Dict[str, tuple]

_locations = {}
_last_weight = {}

_p_locations = {}
_last_p_weight = 0

_inline = {}
_last_i_weight = {}

_globals = {}

_build_timestamps = {}  # type: _Dict[str, str]

_NODE_BIN_DIR = _path.join(_reg.get('paths.root'), 'node_modules', '.bin')
_REQUIRED_NPM_PACKAGES = [
    'gulp', 'gulp-rename', 'gulp-ignore', 'gulp-minify', 'gulp-less', 'gulp-cssmin', 'gulp-babel',
    'babel-preset-es2015', 'gulp-browserify', 'babelify', 'vue', 'vueify', 'babel-plugin-transform-runtime'
]
_GULPFILE = _path.join(_path.realpath(_path.dirname(__file__)), 'gulpfile.js')
_GULP_TASKS_FILE = _path.join(_reg.get('paths.tmp'), 'gulp-tasks.json')


def _run_process(cmd: list, debug: bool = False) -> _subprocess.CompletedProcess:
    """Run process.
    """
    stdout = stderr = _subprocess.PIPE

    if debug and _reg.get('env.type') == 'console':
        stdout = stderr = None

    return _subprocess.run(cmd, stdout=stdout, stderr=stderr)


def _run_node_bin(bin_name: str, *args, **kwargs) -> _subprocess.CompletedProcess:
    """Run Node's binary.
    """
    args_l = []
    for k, v in kwargs.items():
        if isinstance(v, bool):
            v = 'yes' if v else 'no'
        args_l.append('--{}={}'.format(k, v))

    cmd = ['node', _path.join(_NODE_BIN_DIR, bin_name)] + args_l + list(args)

    try:
        r = _run_process(cmd, kwargs.get('debug', False))
        r.check_returncode()
        return r
    except _subprocess.CalledProcessError:
        raise RuntimeError('None-zero exit status while running command {}'.format(cmd))


def register_package(package_name: str, assets_dir: str = 'res/assets', alias: str = None):
    """Register assets container.
    """
    try:
        resolve_package_name(package_name)
        raise _error.PackageAlreadyRegistered(package_name)
    except _error.PackageNotRegistered:
        pass

    pkg_spec = _find_spec(package_name)
    if not pkg_spec:
        raise RuntimeError("Package '{}' is not found".format(package_name))

    # Absolute path to package's assets source directory
    assets_src_path = _path.abspath(_path.join(_path.dirname(pkg_spec.origin), assets_dir))
    if not _path.isdir(assets_src_path):
        FileNotFoundError("Directory '{}' is not found".format(assets_src_path))

    # Absolute path to package's assets destination directory
    assets_path = _reg.get('paths.assets')
    if not assets_path:
        raise RuntimeError("It seems you call register_package('{}') too early".format(package_name))
    assets_dst_path = _path.join(assets_path, package_name)

    _package_paths[package_name] = (assets_src_path, assets_dst_path)

    if package_name.startswith('plugins.') and not alias:
        alias = package_name.split('.')[1]

    if alias:
        if alias in _package_aliases:
            raise _error.PackageAliasAlreadyUsed(alias)

        _package_aliases[alias] = package_name


def library(name: str, assets: _Union[_List, _Callable[..., _List]]):
    """Define a library of assets.
    """
    if name in _libraries:
        raise _error.LibraryAlreadyRegistered(name)

    if is_package_registered(name):
        raise _error.PackageAlreadyRegistered(name)

    _libraries[name] = assets


def is_package_registered(package_name_or_alias: str):
    """Check if the package is registered.
    """
    return package_name_or_alias in _package_paths or package_name_or_alias in _package_aliases


def get_src_dir_path(package_name_or_alias: str) -> str:
    return _package_paths[resolve_package_name(package_name_or_alias)][0]


def get_dst_dir_path(package_name_or_alias: str) -> str:
    return _package_paths[resolve_package_name(package_name_or_alias)][1]


def _get_build_timestamp(package_name_or_alias: str) -> str:
    pkg_name = resolve_package_name(package_name_or_alias)

    if pkg_name not in _build_timestamps:
        f_path = _path.join(get_dst_dir_path(pkg_name), 'timestamp')
        try:
            with open(f_path, 'rt') as f:
                _build_timestamps[pkg_name] = f.readline()
        except FileNotFoundError:
            raise FileNotFoundError("File '{}' is not found. Try to run 'console assetman:build'.".format(f_path))

    return _build_timestamps[pkg_name]


def resolve_package_name(package_name_or_alias) -> str:
    package_name = package_name_or_alias

    if package_name_or_alias in _package_aliases:
        package_name = _package_aliases[package_name_or_alias]

    if package_name not in _package_paths:
        raise _error.PackageNotRegistered(package_name_or_alias)

    return package_name


def detect_collection(location: str) -> str:
    if location.find('.js') > 0:
        return 'js'
    elif location.find('.css') > 0:
        return 'css'
    else:
        raise ValueError("Cannot determine collection of location '{}'.".format(location))


def preload(location: str, permanent: bool = False, collection: str = None, weight: int = 0, **kwargs):
    """Add an asset.
    """
    if not permanent and not _router.request():
        raise RuntimeError('Non permanent assets only allowed while processing HTTP requests')

    path_prefix = kwargs.get('path_prefix')
    exclude_path_prefix = kwargs.get('exclude_path_prefix')
    head = kwargs.get('head')
    async = kwargs.get('async')
    defer = kwargs.get('defer')

    # Library
    if location in _libraries:
        if callable(_libraries[location]):
            assets = _libraries[location](**kwargs)  # type: _List
        else:
            assets = _libraries[location]  # type: _List

        if not isinstance(_libraries[location], _List):
            raise TypeError('List expected')

        for asset_location in assets:
            preload(asset_location, permanent, collection, weight, path_prefix=path_prefix,
                    exclude_path_prefix=exclude_path_prefix, async=async, defer=defer, head=head)

        return

    # Determine collection
    if not collection:
        collection = detect_collection(location)

    if path_prefix:
        if not isinstance(path_prefix, (list, tuple)):
            path_prefix = [path_prefix]
    else:
        path_prefix = []

    if exclude_path_prefix:
        if not isinstance(exclude_path_prefix, (list, tuple)):
            exclude_path_prefix = [exclude_path_prefix]
    else:
        exclude_path_prefix = []

    tid = _threading.get_id()
    if tid not in _locations:
        _locations[tid] = {}

    location_hash = _util.md5_hex_digest(str((location, path_prefix, exclude_path_prefix)))

    if location_hash not in _p_locations and location_hash not in _locations[tid]:
        if permanent:
            global _last_p_weight

            if not weight:
                _last_p_weight += 10
                weight = _last_p_weight
            elif weight > _last_p_weight:
                _last_p_weight = weight

            _p_locations[location_hash] = (location, collection, weight, path_prefix, exclude_path_prefix, async,
                                           defer, head)
        else:
            if not weight:
                _last_weight[tid] += 10
                weight = _last_weight[tid]
            elif weight > _last_weight[tid]:
                _last_weight[tid] = weight

            _locations[tid][location_hash] = (location, collection, weight, path_prefix, exclude_path_prefix, async,
                                              defer, head)


def add_inline(s: str, weight=0):
    """Add a code which intended to output in the document.
    """
    tid = _threading.get_id()

    if not weight:
        _last_i_weight[tid] += 10
    elif weight > _last_i_weight[tid]:
        _last_i_weight[tid] = weight

    _inline[tid].append((s, weight))


def remove(location):
    """Remove an asset location.
    """
    tid = _threading.get_id()
    if tid not in _locations:
        return

    # Location as a string
    if isinstance(location, str):
        _locations[tid] = {k: v for k, v in _locations[tid].items() if location != v[0]}
    # Location as a compiled regular expression
    elif not isinstance(location, str) and location.__class__.__name__ == 'SRE_Pattern':
        _locations[tid] = {k: v for k, v in _locations[tid].items() if not location.match(v[0])}
    else:
        raise TypeError('String or compiled regular expression expected.')


def reset():
    """Remove all previously added locations and inline code except 'permanent'.
    """
    global _last_weight

    tid = _threading.get_id()

    _locations[tid] = {}
    _last_weight[tid] = 0
    _inline[tid] = []
    _last_i_weight[tid] = 0


def get_locations(collection: str = None, filter_path: bool = True) -> list:
    tid = _threading.get_id()

    p_locations = _p_locations.values()
    locations = _locations[tid].values()

    locations = sorted(p_locations, key=lambda x: x[2]) + sorted(locations, key=lambda x: x[2])

    # Filter by collection
    if collection:
        locations = [l for l in locations if l[1] == collection]

    # Filter by path prefix inclusion/exclusion
    if filter_path:
        current_path = _router.current_path()

        filtered_locations = []

        for l in locations:
            # Filter in inclusions
            if l[3]:
                for path_prefix in l[3]:
                    if current_path.startswith(path_prefix):
                        filtered_locations.append(l)
            else:
                filtered_locations.append(l)

            # Filter out exclusions
            if l[4]:
                for exclude_path_prefix in l[4]:
                    if current_path.startswith(exclude_path_prefix):
                        filtered_locations.remove(l)

        locations = filtered_locations

    # Build unique list.
    # Duplicates are possible because same location may be added more than once with different path prefixes.
    added = []
    r = []
    for l in locations:
        if l[0] not in added:
            added.append(l[0])
            r.append(l)

    return r


def get_inline() -> list:
    tid = _threading.get_id()
    if tid not in _inline:
        return []

    return sorted(_inline[tid], key=lambda x: x[1])


def dump_js(html_escape: bool = True, head: bool = False) -> str:
    """Dump JS links.
    """
    r = ''
    for loc in get_locations('js'):
        l_url = url(_util.escape_html(loc[0])) if html_escape else url(loc[0])
        l_async = ' async' if loc[4] else ''
        l_defer = ' defer' if loc[5] else ''
        l_head = loc[6]

        if (not head and not l_head) or (head and l_head):
            r += '<script type="text/javascript" src="{}"{}{}></script>\n'.format(l_url, l_async, l_defer)

    return r


def dump_css(html_escape: bool = True) -> str:
    """Dump CSS links.
    """
    r = ''
    for loc_url in get_urls('css'):
        if html_escape:
            loc_url = _util.escape_html(loc_url)

        r += '<link rel="stylesheet" href="{}">\n'.format(loc_url)

    return r


def dump_inline() -> str:
    r = ''

    tid = _threading.get_id()
    if tid in _inline:
        for item in _inline[tid]:
            r += item[0]

    return r


def url(location: str) -> str:
    """Get URL of an asset.
    """
    if location.startswith('http') or location.startswith('//'):
        return location

    package_name, asset_path = _split_location(location)

    return _router.url('/assets/{}/{}'.format(package_name, asset_path), strip_lang=True, query={
        'v': _get_build_timestamp(package_name)
    })


def get_urls(collection: str = None, filter_path: bool = True) -> list:
    """Get URLs of all locations in the collection.
    """
    return [url(l[0]) for l in get_locations(collection, filter_path)]


def register_global(name: str, value, overwrite: bool = False):
    """Define a global variable which can be user by LESS compiler, etc.
    """
    global _globals

    if name in _globals and not overwrite:
        raise KeyError("Global '{}' is already defined with value {}".format(name, value))

    _globals[name] = value


def check_setup() -> bool:
    """Check if the all required NPM packages are installed
    """
    # Check for NPM existence
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')

    r = _run_process(['npm', 'list', '--depth', '0', '--parseable'] + _REQUIRED_NPM_PACKAGES)

    return len(r.stdout.decode('utf-8').split('\n')) - 1 >= len(_REQUIRED_NPM_PACKAGES)


def setup():
    """Setup NPM environment
    """
    cwd = _getcwd()

    # Node modules should be installed exactly to the root of the project to get things work
    _chdir(_reg.get('paths.root'))

    # Check for NPM existence
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')

    # Install required public NPM packages
    _console.print_info(_lang.t('assetman@installing_required_npm_packages'))
    if _run_process(['npm', 'install'] + _REQUIRED_NPM_PACKAGES, _reg.get('debug', False)).returncode != 0:
        raise RuntimeError('Error while installing NPM packages: {}'.format(_REQUIRED_NPM_PACKAGES))

    _chdir(cwd)


def npm_update():
    """Update NPM environment
    """
    cwd = _getcwd()

    # Node modules should be installed exactly to the root of the project to get things work
    _chdir(_reg.get('paths.root'))

    # Check for NPM existence
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')

    # Update NPM packages
    _console.print_info(_lang.t('assetman@updating_npm_packages'))
    if _run_process(['npm', 'update'], _reg.get('debug', False)).returncode != 0:
        raise RuntimeError('Error while updating NPM packages')

    _chdir(cwd)


def _add_task(location: str, task_name: str, dst: str = '', **kwargs):
    """Add a transformation task
    """
    if '@' not in location and location.startswith('plugins.'):
        location += '@**'

    pkg_name, src = _split_location(location)
    src = _path.join(get_src_dir_path(pkg_name), src)
    dst = _path.join(get_dst_dir_path(pkg_name), dst)

    _tasks.append((pkg_name, task_name, src, dst, kwargs))


def t_copy(location: str, target: str = ''):
    """Add a location to the copy task
    """
    _add_task(location, 'copy', target)


def t_copy_static(location: str, target: str = ''):
    """Add a location to the copy_static task
    """
    _add_task(location, 'copy_static', target)


def t_css(location: str, target: str = ''):
    """Add a location to the CSS transform task.
    """
    _add_task(location, 'css', target)


def t_less(location: str, target: str = ''):
    """Add a location to the LESS transform task.
    """
    _add_task(location, 'less', target)


def t_js(location: str, target: str = '', babelify: bool = False):
    """Add a location to the JS transform task.
    """
    _add_task(location, 'js', target, babelify=babelify)


def t_browserify(location: str, target: str = '', babelify: bool = False, vueify: bool = False):
    """Add a location to the browserify transform task.
    """
    _add_task(location, 'browserify', target, babelify=babelify, vueify=vueify)


def js_module(name: str, location: str, shim: bool = False, deps: list = None, exports: str = None):
    """Define a RequireJS module.
    """
    if name in _requirejs_modules:
        raise ValueError("RequireJS module '{}' is already defined".format(name))

    _requirejs_modules[name] = (location, shim, deps, exports)


def _update_js_config_file(file_path: str, tpl_name: str, data: dict):
    # Create file if it does not exists
    if not _path.exists(file_path):
        dir_path = _path.dirname(file_path)
        if not _path.exists(dir_path):
            _makedirs(dir_path, 0o755, True)

        with open(file_path, 'wt') as f:
            f.write(_tpl.render(tpl_name, {'data': data}))

    # Read contents of the file
    with open(file_path, 'rt') as f:
        js_str = f.read()
        json_str = js_str.replace('requirejs.config(', '')
        json_str = json_str.replace('define(', '')
        json_str = json_str.replace(');', '')

        try:
            json_data = _json.loads(json_str)  # type: dict
        except _json.JSONDecodeError as e:
            # Remove corrupted file and re-run this function to reconstruct the file
            _console.print_warning('{} is corrupted and will be rebuilt'.format(file_path))
            _unlink(file_path)
            return _update_js_config_file(file_path, tpl_name, data)

    json_data = _util.dict_merge(json_data, data)

    with open(file_path, 'wt') as f:
        f.write(_tpl.render(tpl_name, {'data': json_data}, False))


def _update_requirejs_config(rjs_module_name: str, rjs_module_asset_path: str, shim: bool = False, deps: list = None,
                             exports: str = None):
    f_path = _path.join(_reg.get('paths.assets'), 'plugins.assetman', 'require-config.js')

    data = {
        'paths': {rjs_module_name: rjs_module_asset_path}
    }

    if shim:
        data['shim'] = {rjs_module_name: {
            'deps': deps or []
        }}

        if exports:
            data['shim'][rjs_module_name]['exports'] = exports

    _update_js_config_file(f_path, 'assetman@requirejs-config', data)


def _update_timestamp_config(package_name: str):
    ts = _util.md5_hex_digest(str(_time()))
    _build_timestamps[package_name] = ts

    # Write timestamp to package's assets directory
    package_ts_f_path = _path.join(get_dst_dir_path(package_name), 'timestamp')
    package_ts_d_path = _path.dirname(package_ts_f_path)
    if not _path.exists(package_ts_d_path):
        _makedirs(package_ts_d_path, 0o755, True)
    with open(package_ts_f_path, 'wt') as f:
        f.write(ts)

    # Update JS timestamps config
    js_config_f_path = _path.join(_reg.get('paths.assets'), 'plugins.assetman', 'build-timestamps.js')
    _update_js_config_file(js_config_f_path, 'assetman@build-timestamps', {
        package_name: ts,
    })


def build_translations():
    """Compile translations
    """
    from pytsite import console, tpl
    from plugins import assetman

    console.print_info(_lang.t('assetman@compiling_translations'))

    translations = {}
    for lang_code in _lang.langs():
        translations[lang_code] = {}
        for pkg_name, info in _lang.get_packages().items():
            _logger.info('Compiling translations for {} ({})'.format(pkg_name, lang_code))
            translations[lang_code][pkg_name] = _lang.get_package_translations(pkg_name, lang_code)

    # Write translations to static file
    output_file = _path.join(assetman.get_dst_dir_path('plugins.assetman'), 'lang-translations.js')
    output_dir = _path.dirname(output_file)

    if not _path.exists(output_dir):
        _makedirs(output_dir, 0o755, True)

    with open(output_file, 'wt', encoding='utf-8') as f:
        _logger.info("Writing translations into '{}'".format(output_file))
        f.write(tpl.render('assetman@translations-js', {
            'langs_json': _json.dumps(_lang.langs()),
            'translations_json': _json.dumps(translations),
        }))


def build(package_name: str):
    """Compile assets.
    """
    global _globals

    _console.print_info(_lang.t('assetman@compiling_assets_for_package', {'package': package_name}))

    package_name = resolve_package_name(package_name)
    assets_dst_path = get_dst_dir_path(package_name)

    # Remove package's assets directory
    # Directory of assetman cannot be removed because it contains dynamically generated RequireJS config
    # and timestamps JSON
    if package_name != 'plugins.assetman' and _path.exists(assets_dst_path):
        _rmtree(assets_dst_path)

    # Create tasks file for Gulp
    tasks_file_content = []
    for t_info in _tasks:
        pkg_name, task_name, src, dst, kwargs = t_info
        if package_name == pkg_name:
            tasks_file_content.append({
                'name': task_name,
                'source': src,
                'destination': dst,
                'args': kwargs,
            })

    if not tasks_file_content:
        _update_timestamp_config(package_name)
        raise _error.NoTasksDefined(package_name)

    with open(_GULP_TASKS_FILE, 'wt') as f:
        f.write(_json.dumps(tasks_file_content))

    # Run Gulp
    debug = _reg.get('debug')
    _run_node_bin('gulp', '--silent', gulpfile=_GULPFILE, debug=debug, tasksFile=_GULP_TASKS_FILE)

    # Update timestamp
    _update_timestamp_config(package_name)

    # Update RequireJS config
    for rjs_module_name, rjs_module_asset_data in _requirejs_modules.items():
        m_asset_location = rjs_module_asset_data[0]
        m_shim = rjs_module_asset_data[1]
        m_deps = rjs_module_asset_data[2]
        m_exports = rjs_module_asset_data[3]
        definer_package_name, m_asset_path = _split_location(m_asset_location)
        if package_name != definer_package_name:
            continue

        package_timestamp = _get_build_timestamp(definer_package_name)
        m_asset_path = '{}/{}.js?v={}'.format(definer_package_name, m_asset_path, package_timestamp)
        _update_requirejs_config(rjs_module_name, m_asset_path, m_shim, m_deps, m_exports)


def build_all():
    assets_static_path = _reg.get('paths.assets')

    _console.print_info(_lang.t('assetman@compiling_assets'))

    if _path.exists(assets_static_path):
        _rmtree(assets_static_path)

    for package_name in _package_paths:
        build(package_name)


def on_split_location(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('assetman@split_location', handler, priority)


def _split_location(location: str) -> _Tuple[str, str]:
    """Split asset path into package name and asset path
    """
    for r in _events.fire('assetman@split_location', location=location):
        location = r

    package_name, assets_path = location.split('@')[:2]

    return resolve_package_name(package_name), assets_path
