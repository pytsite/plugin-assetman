"""PytSite Assetman Plugin API Functions
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

import subprocess as _subprocess
import json as _json
from typing import Dict as _Dict, List as _List, Tuple as _Tuple, Union as _Union, Optional as _Optional, \
    Iterable as _Iterable
from os import path as _path, chdir as _chdir, makedirs as _makedirs, getcwd as _getcwd, symlink as _symlink, \
    mkdir as _mkdir, listdir as _listdir
from shutil import rmtree as _rmtree
from importlib.util import find_spec as _find_spec
from pytsite import router as _router, threading as _threading, util as _util, reg as _reg, console as _console, \
    lang as _lang, events as _events, logger as _logger, package_info as _package_info
from . import _error

_packages = {}  # type: _Dict[str, _Tuple[str, str]]
_inline_js = {}
_building_translations = []

_DEBUG = _reg.get('debug', False)
_NODE_BIN_DIR = _path.join(_reg.get('paths.root'), 'node_modules', '.bin')


def _run_process(cmd: list, passthrough: bool = _DEBUG) -> _subprocess.CompletedProcess:
    """Run process.
    """
    stdout = stderr = _subprocess.PIPE if not passthrough else None

    return _subprocess.run(cmd, stdout=stdout, stderr=stderr)


def _run_node_bin(bin_name: str, args: _List[str], passthrough: bool = _DEBUG) -> _subprocess.CompletedProcess:
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


def is_package_registered(package_name: str) -> bool:
    """Check if the package is registered.
    """
    try:
        return bool(resolve_package(package_name))
    except _error.PackageNotRegistered:
        return False


def resolve_package(package_name: str) -> str:
    """Check whether package is registered
    """
    if package_name not in _packages:
        plugin_package_name = 'plugins.' + package_name
        if plugin_package_name in _packages:
            package_name = plugin_package_name
        else:
            raise _error.PackageNotRegistered(package_name)

    return package_name


def assets_src(package_name: str) -> str:
    return _packages[resolve_package(package_name)][0]


def assets_dst(package_name: str) -> str:
    return _packages[resolve_package(package_name)][1]


def assets_public_path(package_name: str) -> str:
    return '/assets/{}/'.format(resolve_package(package_name))


def reset():
    """Reset
    """
    _inline_js[_threading.get_id()] = []


def js(location: str, asynchr: bool = False, defer: bool = False) -> str:
    """Get HTML <script> tags for a location
    """
    location = _util.escape_html(url(location))
    asynchr = ' async' if asynchr else ''
    defer = ' defer' if defer else ''

    return '<script type="text/javascript" src="{}"{}{}></script>'.format(location, asynchr, defer)


def css(location: str) -> str:
    """Get HTML <link rel="stylesheet"> tag for a location
    """
    return '<link rel="stylesheet" href="{}">'.format(_util.escape_html(url(location)))


def inline_js(s: str = None) -> _Optional[str]:
    tid = _threading.get_id()

    if s:
        _inline_js[tid].append(s)
    else:
        return ''.join(_inline_js[tid]) if tid in _inline_js else ''


def url(location: str) -> str:
    """Get URL of an asset.
    """
    if location.startswith('http') or location.startswith('//'):
        return location

    package_name, asset_path = _split_location(location)
    package_name = resolve_package(package_name)

    return _router.url('/assets/{}/{}'.format(package_name, asset_path), add_lang_prefix=False)


def _check_npm_installation():
    """Check if the NPM is installed
    """
    if _run_process(['which', 'npm'], False).returncode != 0:
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

        r = _run_process(['npm', 'install', '--no-save', '--no-audit', '--no-package-lock'] + packages)
        r.check_returncode()

    except _subprocess.CalledProcessError:
        msg = 'Error while installing required NPM package(s): {}'.format(packages)
        raise RuntimeError(msg)

    finally:
        _chdir(cwd)


def install_npm_deps(package_names: _Union[str, _List[str]]):
    """Install NPM packages required by locally installed plugins
    """
    is_dev_host = _path.isdir(_path.join(_reg.get('paths.root'), 'npm_packages'))

    if isinstance(package_names, str):
        package_names = [package_names]

    # Build list of NPM packages required by plugins
    npm_pkgs_to_install = []
    for pkg_name in package_names:
        # Skip package if it does not provide package.json
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

    # Install required NPM packages
    npm_install(npm_pkgs_to_install)


def setup():
    """Setup assetman environment
    """
    _console.print_info(_lang.t('assetman@installing_required_npm_packages'))

    root_dir = _reg.get('paths.root')
    node_modules_subdir = _path.join(_path.join(root_dir, 'node_modules'), '@pytsite')
    dev_host_npm_packages_dir = _path.join(root_dir, 'npm_packages')
    is_dev_host = _path.isdir(dev_host_npm_packages_dir)

    _makedirs(node_modules_subdir, 0o755, True)

    # Create symlinks in node_modules from npm_packages
    if is_dev_host:
        for name in _listdir(dev_host_npm_packages_dir):
            src = _path.join(dev_host_npm_packages_dir, name)
            if _path.isdir(src):
                dst = _path.join(node_modules_subdir, name)
                if not _path.exists(dst):
                    _symlink(src, dst)

    # Create symlinks in node_modules from registered packages which have package.json
    for pkg_name in _packages:
        src_dir = assets_src(pkg_name)
        if not _path.exists(_path.join(src_dir, 'package.json')):
            continue

        node_pkg_name = pkg_name.replace('plugins.', '').replace('_', '-').replace('.', '-')
        node_modules_pkg_dir = _path.join(node_modules_subdir, node_pkg_name)
        if not _path.exists(node_modules_pkg_dir):
            _symlink(src_dir, node_modules_pkg_dir)

    # Install NPM packages required by plugins
    install_npm_deps(list(_packages.keys()))


def build_translations(pkg_name: str):
    """Compile translations
    """
    # Manage with recursive calls
    if pkg_name in _building_translations:
        return

    _building_translations.append(pkg_name)

    # Build dependencies
    for dep_pkg_name in _package_info.requires_plugins(pkg_name):
        dep_pkg_name = 'plugins.' + dep_pkg_name
        if _lang.is_package_registered(dep_pkg_name):
            build_translations(dep_pkg_name)

    output_file = _path.join(assets_dst('assetman'), 'translations.json')

    # Prepare data structure
    if _path.exists(output_file):
        data = _util.load_json(output_file)
    else:
        data = {'langs': {}, 'translations': {}}

    # Update languages information
    data['langs'] = _lang.langs()

    # Build translations structure
    for lang_code in _lang.langs():
        if lang_code not in data['translations']:
            data['translations'][lang_code] = {}
        _logger.info('Compiling translations for {} ({})'.format(pkg_name, lang_code))
        data['translations'][lang_code][pkg_name] = _lang.get_package_translations(pkg_name, lang_code)

    # Create output directory
    output_dir = _path.dirname(output_file)
    if not _path.exists(output_dir):
        _makedirs(output_dir, 0o755, True)

    # Write translations to teh file
    with open(output_file, 'wt', encoding='utf-8') as f:
        _logger.debug("Writing translations into '{}'".format(output_file))
        f.write(_json.dumps(data))


def build(pkg_name: str, debug: bool = _DEBUG, mode: str = None, watch: bool = False):
    """Compile assets
    """
    pkg_name = resolve_package(pkg_name)
    src = assets_src(pkg_name)
    dst = assets_dst(pkg_name)
    public_path = assets_public_path(pkg_name)
    mode = mode or ('development' if debug else 'production')

    # Build translations
    if _lang.is_package_registered(pkg_name):
        build_translations(pkg_name)

    # Building is possible only if 'webpack.config.js' exists
    webpack_config = _path.join(src, 'webpack.config.js')
    if not _path.exists(webpack_config):
        return

    # Clear destination directory
    if _path.exists(dst):
        _rmtree(dst)

    webpack_parts = []
    root_dir = _reg.get('paths.root') + '/'
    for p in _packages.values():
        if _path.exists(_path.join(p[0], 'webpack.part.js')):
            webpack_parts.append(p[0].replace(root_dir, ''))

    # Run webpack
    _console.print_info(_lang.t('assetman@compiling_assets_for_package', {'package': pkg_name}))
    args = [
        '--mode', mode,
        '--config', webpack_config,
        '--context', assets_src(pkg_name),
        '--output-path', dst,
        '--output-public-path', public_path,
        '--env.NODE_ENV', mode,
        '--env.root_dir', root_dir,
        '--env.config_parts', ','.join(webpack_parts),
        '--watch', str(watch).lower(),
    ]

    _run_node_bin('webpack-cli', args, watch or debug)


def build_all(debug: bool = _DEBUG, mode: str = None):
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
        build(pkg_name, debug, mode)


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
