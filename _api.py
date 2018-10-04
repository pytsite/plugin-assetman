"""PytSite Assetman Plugin API Functions
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

import subprocess as _subprocess
import json as _json
from typing import Dict as _Dict, List as _List, Tuple as _Tuple, Union as _Union
from os import path as _path, chdir as _chdir, makedirs as _makedirs, getcwd as _getcwd, symlink as _symlink, \
    mkdir as _mkdir, listdir as _listdir
from shutil import rmtree as _rmtree
from importlib.util import find_spec as _find_spec
from pytsite import router as _router, threading as _threading, util as _util, reg as _reg, console as _console, \
    lang as _lang, events as _events, logger as _logger
from . import _error

_packages = {}  # type: _Dict[str, _Tuple[str, str]]

_locations = {}
_last_weight = {}

_p_locations = {}  # Permanent locations
_last_p_weight = 0

_inline_js = {}
_last_i_weight = {}

_DEV_MODE = _reg.get('debug', False)
_NODE_BIN_DIR = _path.join(_reg.get('paths.root'), 'node_modules', '.bin')


def _run_process(cmd: list, passthrough: bool = False) -> _subprocess.CompletedProcess:
    """Run process.
    """
    stdout = stderr = _subprocess.PIPE if not passthrough else None

    return _subprocess.run(cmd, stdout=stdout, stderr=stderr)


def _run_node_bin(bin_name: str, args: _List[str], passthrough: bool = False) -> _subprocess.CompletedProcess:
    """Run Node's binary
    """
    cmd = ['node', _path.join(_NODE_BIN_DIR, bin_name)] + args
    r = _run_process(cmd, passthrough)

    try:
        r.check_returncode()
        return r
    except _subprocess.CalledProcessError:
        raise RuntimeError('None-zero exit status while executing command: {}'.format(' '.join(cmd)))


def register_package(package_name: str, assets_dir: str = 'res/assets'):
    """Register PytSite package which contains assets
    """
    pkg_spec = _find_spec(package_name)
    if not pkg_spec:
        raise RuntimeError("Package '{}' is not found".format(package_name))

    # Shorten name for plugins
    if package_name.startswith('plugins.'):
        package_name = package_name.split('.')[1]

    # Check whether assetman's package is already registered
    if package_name in _packages:
        raise _error.PackageAlreadyRegistered(package_name)

    # Absolute path to package's assets source directory
    src_path = _path.abspath(_path.join(_path.dirname(pkg_spec.origin), assets_dir))
    if not _path.isdir(src_path):
        FileNotFoundError("Directory '{}' is not found".format(src_path))

    # Absolute path to package's assets destination directory
    assets_path = _reg.get('paths.assets')
    if not assets_path:
        raise RuntimeError("It seems you call register_package('{}') too early".format(package_name))
    dst_path = _path.join(assets_path, package_name)

    _packages[package_name] = (src_path, dst_path)


def is_package_registered(package_name: str):
    """Check if the package is registered.
    """
    return package_name in _packages


def resolve_package(package_name: str) -> str:
    """Check whether package is registered
    """
    if package_name not in _packages:
        raise _error.PackageNotRegistered(package_name)

    return package_name


def assets_src(package_name: str) -> str:
    return _packages[resolve_package(package_name)][0]


def assets_dst(package_name: str) -> str:
    return _packages[resolve_package(package_name)][1]


def assets_public_path(package_name: str) -> str:
    return '/assets/{}/'.format(resolve_package(package_name))


def preload(location: str, permanent: bool = False, collection: str = None, weight: int = 0, **kwargs):
    """Preload an asset
    """
    if not permanent and not _router.request():
        raise RuntimeError('Non permanent assets only allowed while processing HTTP requests')

    head = kwargs.get('head')
    asynchr = kwargs.get('asynchr')
    defer = kwargs.get('defer')

    # Determine collection
    if not collection:
        if '.js' in location:
            collection = 'js'
        elif '.css' in location:
            collection = 'css'
        else:
            raise ValueError("Cannot determine collection of location '{}'.".format(location))

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

    return _router.url('/assets/{}/{}'.format(package_name, asset_path), add_lang_prefix=False)


def _check_npm_installation():
    """Check if the NPM is installed
    """
    if _run_process(['which', 'npm']).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')


def npm_install(packages: _Union[str, _List[str]]):
    """Install NPM package(s)
    """
    _check_npm_installation()
    cwd = _getcwd()

    try:
        # Node modules should be installed exactly to the root of the project to get things work
        _chdir(_reg.get('paths.root'))
        if isinstance(packages, str):
            packages = [packages]

        r = _run_process(['npm', 'install', '--no-save', '--no-audit', '--no-package-lock'] + packages, True)
        r.check_returncode()

    except _subprocess.CalledProcessError:
        msg = 'Error while installing required NPM package(s): {}'.format(packages)
        raise RuntimeError(msg)

    finally:
        _chdir(cwd)


def setup():
    """Setup assetman environment
    """
    _console.print_info(_lang.t('assetman@installing_required_npm_packages'))

    root_dir = _reg.get('paths.root')
    node_modules_subdir = _path.join(_path.join(root_dir, 'node_modules'), '@pytsite')
    dev_host_npm_packages_dir = _path.join(root_dir, 'npm_packages')
    is_dev_host = _path.isdir(dev_host_npm_packages_dir)

    # Create symlinks in node_modules from npm_packages
    if is_dev_host:
        for name in _listdir(dev_host_npm_packages_dir):
            src = _path.join(dev_host_npm_packages_dir, name)
            if _path.isdir(src):
                dst = _path.join(node_modules_subdir, name)
                if not _path.exists(dst):
                    _symlink(src, dst)

    # Create symlinks in node_modules from plugins
    for pkg_name in _packages:
        src_dir = assets_src(pkg_name)
        if not _path.exists(_path.join(src_dir, 'package.json')):
            continue

        node_pkg_name = pkg_name.replace('plugins.', '').replace('_', '-').replace('.', '-')
        node_modules_pkg_dir = _path.join(node_modules_subdir, node_pkg_name)
        if not _path.exists(node_modules_pkg_dir):
            _symlink(src_dir, node_modules_pkg_dir)

    # Install NPM packages required by plugins
    npm_pkgs_to_install = []
    for pkg_name in _packages:
        # Skip plugin if it does not provide package.json
        json_path = _path.join(assets_src(pkg_name), 'package.json')
        if not _path.exists(json_path):
            continue

        # Collect dependencies
        json = _util.load_json(json_path)
        for name, ver in json.get('dependencies', {}).items():
            if name.startswith('@pytsite') and is_dev_host:
                continue
            npm_pkg_spec = '{}@{}'.format(name, ver)
            if npm_pkg_spec not in npm_pkgs_to_install:
                npm_pkgs_to_install.append(npm_pkg_spec)

    npm_install(npm_pkgs_to_install)


def build_translations():
    """Compile translations
    """
    from pytsite import console
    console.print_info(_lang.t('assetman@compiling_translations'))

    translations = {}
    for lang_code in _lang.langs():
        translations[lang_code] = {}
        for pkg_name, info in _lang.get_packages().items():
            _logger.debug('Compiling translations for {} ({})'.format(pkg_name, lang_code))
            translations[lang_code][pkg_name] = _lang.get_package_translations(pkg_name, lang_code)

    # Write translations to static file
    output_file = _path.join(assets_dst('assetman'), 'translations.json')
    output_dir = _path.dirname(output_file)

    if not _path.exists(output_dir):
        _makedirs(output_dir, 0o755, True)

    with open(output_file, 'wt', encoding='utf-8') as f:
        _logger.debug("Writing translations into '{}'".format(output_file))
        f.write(_json.dumps({
            'langs': _lang.langs(),
            'translations': translations,
        }))


def build(pkg_name: str, debug: bool = _DEV_MODE):
    """Compile assets
    """
    pkg_name = resolve_package(pkg_name)
    src = assets_src(pkg_name)
    dst = assets_dst(pkg_name)
    public_path = assets_public_path(pkg_name)
    mode = 'development' if _DEV_MODE else 'production'

    # Clear destination directory
    if _path.exists(dst):
        _rmtree(dst)

    webpack_config = _path.join(src, 'webpack.config.js')
    if not _path.exists(webpack_config):
        return

    # Run webpack
    _console.print_info(_lang.t('assetman@compiling_assets_for_package', {'package': pkg_name}))
    args = [
        '--mode', mode,
        '--config', webpack_config,
        '--context', assets_src(pkg_name),
        '--output-path', dst,
        '--output-public-path', public_path,
        '--env.NODE_ENV', 'development' if _DEV_MODE else 'production',
        '--env.plugins_dir', _reg.get('paths.plugins'),
    ]
    _run_node_bin('webpack-cli', args, debug)


def build_all(debug: bool = _DEV_MODE):
    _console.print_info(_lang.t('assetman@compiling_assets'))

    assets_static_path = _reg.get('paths.assets')
    node_modules_dir = _path.join(_reg.get('paths.root'), 'node_modules')
    node_modules_subdir = _path.join(node_modules_dir, '@pytsite')

    if not _path.isdir(node_modules_dir):
        raise FileNotFoundError("'{}' directory is not exists. Check your NPM installation.")

    if not _path.isdir(node_modules_subdir):
        _mkdir(node_modules_subdir, 0o755)

    if _path.exists(assets_static_path):
        _rmtree(assets_static_path)

    for pkg_name in _packages:
        build(pkg_name, debug)

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

    return resolve_package(package_name), assets_path
