"""PytSite Assetman Plugin API Functions
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

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

_package_paths = {}  # type: _Dict[str, _Tuple[str, str]]
_package_aliases = {}  # type: _Dict[str, str]
_libraries = {}  # type: _Dict[str, _Union[_List, _Callable[[...], _List]]]

_tasks = []  # type: _List[_Tuple]
_requirejs_modules = {}  # type: _Dict[str, tuple]

_locations = {}
_last_weight = {}

_p_locations = {}  # Permanent locations
_last_p_weight = 0

_inline_js = {}
_last_i_weight = {}

_globals = {}

_build_timestamps = {}  # type: _Dict[str, str]

_DEBUG = _reg.get('debug', False)
_NODE_BIN_DIR = _path.join(_reg.get('paths.root'), 'node_modules', '.bin')
_REQUIRED_NPM_PACKAGES = [
    'yargs', 'gulp', 'gulp-rename', 'gulp-ignore', 'gulp-minify', 'gulp-less', 'gulp-sass', 'gulp-cssmin', 'gulp-babel',
    'babel-core', 'babel-preset-env',
]
_GULPFILE = _path.join(_path.realpath(_path.dirname(__file__)), 'gulpfile.js')
_GULP_TASKS_FILE = _path.join(_reg.get('paths.tmp'), 'gulp-tasks.json')


def _run_process(cmd: list, passthrough: bool = False) -> _subprocess.CompletedProcess:
    """Run process.
    """
    stdout = stderr = _subprocess.PIPE if not passthrough else None

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
    r = _run_process(cmd)

    try:
        r.check_returncode()
        return r
    except _subprocess.CalledProcessError:
        raise RuntimeError('None-zero exit status while executing "{}":\n\n{}'.
                           format(' '.join(cmd), r.stderr.decode('utf-8')))


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


def library(name: str, assets: _Union[str, _List[str]]):
    """Define a library of assets
    """
    if name in _libraries:
        raise _error.LibraryAlreadyRegistered(name)

    if is_package_registered(name):
        raise _error.PackageAlreadyRegistered(name)

    if isinstance(assets, str):
        assets = [assets]
    elif not isinstance(assets, list):
        raise TypeError('List or string expected, got {}'.format(type(assets)))

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


def _detect_collection(location: str) -> str:
    if '.js' in location:
        return 'js'
    elif '.css' in location:
        return 'css'
    else:
        raise ValueError("Cannot determine collection of location '{}'.".format(location))


def preload(location: str, permanent: bool = False, collection: str = None, weight: int = 0, **kwargs):
    """Preload an asset
    """
    if not permanent and not _router.request():
        raise RuntimeError('Non permanent assets only allowed while processing HTTP requests')

    head = kwargs.get('head')
    asynchr = kwargs.get('asynchr')
    defer = kwargs.get('defer')

    # Library
    if location in _libraries:
        for asset_location in _libraries[location]:
            preload(asset_location, permanent, collection, weight, asynchr=asynchr, defer=defer, head=head)
        return

    # Determine collection
    if not collection:
        collection = _detect_collection(location)

    tid = _threading.get_id()
    if tid not in _locations:
        _locations[tid] = {}

    location_hash = _util.md5_hex_digest(str(location))

    if location_hash not in _p_locations and location_hash not in _locations[tid]:
        if permanent:
            global _last_p_weight

            if not weight:
                _last_p_weight += 10
                weight = _last_p_weight
            elif weight > _last_p_weight:
                _last_p_weight = weight

            _p_locations[location_hash] = (location, collection, weight, asynchr, defer, head)
        else:
            if not weight:
                _last_weight[tid] += 10
                weight = _last_weight[tid]
            elif weight > _last_weight[tid]:
                _last_weight[tid] = weight

            _locations[tid][location_hash] = (location, collection, weight, asynchr, defer, head)


def add_inline_js(s: str, weight=0):
    """Add a code which intended to output in the HTTP response body
    """
    tid = _threading.get_id()

    if not weight:
        _last_i_weight[tid] += 10
    elif weight > _last_i_weight[tid]:
        _last_i_weight[tid] = weight

    _inline_js[tid].append((s, weight))


def reset():
    """Remove all previously added locations and inline code except 'permanent'.
    """
    global _last_weight

    tid = _threading.get_id()

    _locations[tid] = {}
    _last_weight[tid] = 0
    _inline_js[tid] = []
    _last_i_weight[tid] = 0


def _get_locations(collection: str = None) -> list:
    tid = _threading.get_id()

    p_locations = _p_locations.values()
    locations = _locations[tid].values()

    locations = sorted(p_locations, key=lambda x: x[2]) + sorted(locations, key=lambda x: x[2])

    # Filter by collection
    if collection:
        locations = [l for l in locations if l[1] == collection]

    return locations


def js_tag(location: str, asynchr: bool = False, defer: bool = False) -> str:
    """Get HTML <script> tags for a location
    """
    if location in _libraries:
        return '\n'.join([js_tag(l, asynchr, defer) for l in _libraries[location] if _detect_collection(l) == 'js'])

    location = _util.escape_html(url(location))
    asynchr = ' async' if asynchr else ''
    defer = ' defer' if defer else ''

    return '<script type="text/javascript" src="{}"{}{}></script>'.format(location, asynchr, defer)


def js_tags(head: bool = False) -> str:
    """Get HTML <script> tags for all preloaded links
    """
    r = ''
    for l_info in _get_locations('js'):
        if (not head and not l_info[5]) or (head and l_info[5]):
            r += js_tag(l_info[0], l_info[3], l_info[4]) + '\n'

    return r


def css_tag(location: str) -> str:
    """Get HTML <link rel="stylesheet"> tag for a location
    """
    if location in _libraries:
        return '\n'.join([css_tag(l) for l in _libraries[location] if _detect_collection(l) == 'css'])

    return '<link rel="stylesheet" href="{}">'.format(_util.escape_html(url(location)))


def css_tags() -> str:
    """Get HTML <link rel="stylesheet"> tags of preloaded locations
    """
    return '\n'.join([css_tag(l_info[0]) for l_info in _get_locations('css')])


def inline_js() -> str:
    r = ''

    tid = _threading.get_id()
    if tid in _inline_js:
        for item in sorted(_inline_js[tid], key=lambda x: x[1]):
            r += item[0]

    return r


def url(location: str) -> str:
    """Get URL of an asset.
    """
    if location.startswith('http') or location.startswith('//'):
        return location

    package_name, asset_path = _split_location(location)

    return _router.url('/assets/{}/{}'.format(package_name, asset_path), add_lang_prefix=False, query={
        'v': _get_build_timestamp(package_name)
    })


def urls(collection: str = None) -> list:
    """Get URLs of all locations in the collection.
    """
    return [url(l[0]) for l in _get_locations(collection)]


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


def npm_install(package: _Union[str, _List[str]]):
    """Install NPM package(s)
    """
    # Check for NPM existence
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')

    cwd = _getcwd()

    try:
        # Node modules should be installed exactly to the root of the project to get things work
        _chdir(_reg.get('paths.root'))

        r = _run_process(['npm', 'install', '--no-save', '--no-audit', '--no-package-lock'] + package, _DEBUG)
        r.check_returncode()

    except _subprocess.CalledProcessError as e:
        msg = 'Error while installing required NPM package(s): {}'.format(package)
        if not _DEBUG:
            msg += '\n\n{}'.format(e.stderr)
        raise RuntimeError(msg)

    finally:
        _chdir(cwd)


def npm_update():
    """Update all installed NPM packages
    """
    cwd = _getcwd()

    # Node modules should be installed exactly to the root of the project to get things work
    _chdir(_reg.get('paths.root'))

    # Check for NPM existence
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')

    # Update NPM packages
    _console.print_info(_lang.t('assetman@updating_npm_packages'))
    if _run_process(['npm', 'update'], _DEBUG).returncode != 0:
        raise RuntimeError('Error while updating NPM packages')

    _chdir(cwd)


def setup():
    """Setup NPM environment
    """
    # Install required NPM packages
    _console.print_info(_lang.t('assetman@installing_required_npm_packages'))
    npm_install(_REQUIRED_NPM_PACKAGES)


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


def t_scss(location: str, target: str = ''):
    """Add a location to the SCSS transform task.
    """
    _add_task(location, 'scss', target)


def t_js(location: str, target: str = '', babelify: bool = False):
    """Add a location to the JS transform task.
    """
    _add_task(location, 'js', target, babelify=babelify)


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
        except _json.JSONDecodeError:
            # Remove corrupted file and re-run this function to reconstruct the file
            _console.print_warning('{} is corrupted and will be rebuilt'.format(file_path))
            _unlink(file_path)
            return _update_js_config_file(file_path, tpl_name, data)

    json_data = _util.dict_merge(json_data, data)
    for k, v in json_data.items():
        if isinstance(v, list):
            json_data[k] = _util.cleanup_list(v, True)

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


def _update_package_aliases_config(package_name: str):
    js_config_f_path = _path.join(_reg.get('paths.assets'), 'plugins.assetman', 'package-aliases.js')

    for alias, p_name in _package_aliases.items():
        if package_name == p_name:
            _update_js_config_file(js_config_f_path, 'assetman@package-aliases', {alias: p_name})


def _update_libraries_config():
    js_config_f_path = _path.join(_reg.get('paths.assets'), 'plugins.assetman', 'libraries.js')
    _update_js_config_file(js_config_f_path, 'assetman@libraries', _libraries)


def build_translations():
    """Compile translations
    """
    from pytsite import console, tpl
    console.print_info(_lang.t('assetman@compiling_translations'))

    translations = {}
    for lang_code in _lang.langs():
        translations[lang_code] = {}
        for pkg_name, info in _lang.get_packages().items():
            if not info['__is_alias']:
                _logger.debug('Compiling translations for {} ({})'.format(pkg_name, lang_code))
                translations[lang_code][pkg_name] = _lang.get_package_translations(pkg_name, lang_code)

    # Write translations to static file
    output_file = _path.join(get_dst_dir_path('plugins.assetman'), 'lang-translations.js')
    output_dir = _path.dirname(output_file)

    if not _path.exists(output_dir):
        _makedirs(output_dir, 0o755, True)

    with open(output_file, 'wt', encoding='utf-8') as f:
        _logger.debug("Writing translations into '{}'".format(output_file))
        f.write(tpl.render('assetman@translations-js', {
            'langs_json': _json.dumps(_lang.langs()),
            'translations_json': _json.dumps(translations),
        }))


def build(package_name: str):
    """Compile assets
    """
    global _globals

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
        return

    _console.print_info(_lang.t('assetman@compiling_assets_for_package', {'package': package_name}))

    with open(_GULP_TASKS_FILE, 'wt') as f:
        f.write(_json.dumps(tasks_file_content))

    # Run Gulp
    _run_node_bin('gulp', '--silent', gulpfile=_GULPFILE, tasksFile=_GULP_TASKS_FILE, minify=not _DEBUG)

    # Update timestamp
    _update_timestamp_config(package_name)

    # Update package aliases config
    _update_package_aliases_config(package_name)

    # Update libraries config
    _update_libraries_config()

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

    build_translations()


def on_split_location(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('assetman@split_location', handler, priority)


def _split_location(location: str) -> _Tuple[str, str]:
    """Split asset path into package name and asset path
    """
    for r in _events.fire('assetman@split_location', location=location):
        location = r

    package_name, assets_path = location.split('@')[:2] if '@' in location else ['app', location]

    return resolve_package_name(package_name), assets_path
