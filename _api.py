"""PytSite Assetman Plugin API Functions
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

import subprocess as subprocess
import json as _json
from typing import Dict, List, Tuple, Union, Optional
from os import path, chdir, makedirs, getcwd, symlink, mkdir, listdir
from shutil import rmtree
from importlib.util import find_spec
from pytsite import router, threading, util, reg, console, lang, events, logger, package_info
from . import _error

_packages = {}  # type: Dict[str, Tuple[str, str]]
_inline_js = {}
_building_translations = []

_DEBUG = reg.get('debug', False)
_NODE_BIN_DIR = path.join(reg.get('paths.root'), 'node_modules', '.bin')


def _run_process(cmd: list, passthrough: bool = _DEBUG) -> subprocess.CompletedProcess:
    """Run process.
    """
    stdout = stderr = subprocess.PIPE if not passthrough else None

    return subprocess.run(cmd, stdout=stdout, stderr=stderr)


def _run_node_bin(bin_name: str, args: List[str], passthrough: bool = _DEBUG) -> subprocess.CompletedProcess:
    """Run Node's binary
    """
    cmd = ['node', path.join(_NODE_BIN_DIR, bin_name)] + args
    r = _run_process(cmd, passthrough)

    try:
        r.check_returncode()
        return r
    except subprocess.CalledProcessError:
        raise RuntimeError('None-zero exit status while executing command: {}'.format(' '.join(cmd)))


def register_package(package_name: str, assets_dir: str = 'res/assets'):
    """Register PytSite package which contains assets
    """
    pkg_spec = find_spec(package_name)
    if not pkg_spec:
        raise RuntimeError("Package '{}' is not found".format(package_name))

    # Check whether assetman's package is already registered
    if package_name in _packages:
        raise _error.PackageAlreadyRegistered(package_name)

    # Absolute path to package's assets source directory
    src_path = path.abspath(path.join(path.dirname(pkg_spec.origin), assets_dir))
    if not path.isdir(src_path):
        FileNotFoundError("Directory '{}' is not found".format(src_path))

    # Absolute path to package's assets destination directory
    assets_path = reg.get('paths.assets')
    if not assets_path:
        raise RuntimeError("It seems you call register_package('{}') too early".format(package_name))
    dst_path = path.join(assets_path, package_name)

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
    _inline_js[threading.get_id()] = []


def js(location: str, asynchr: bool = False, defer: bool = False) -> str:
    """Get HTML <script> tags for a location
    """
    location = util.escape_html(url(location))
    asynchr = ' async' if asynchr else ''
    defer = ' defer' if defer else ''

    return '<script type="text/javascript" src="{}"{}{}></script>'.format(location, asynchr, defer)


def css(location: str) -> str:
    """Get HTML <link rel="stylesheet"> tag for a location
    """
    return '<link rel="stylesheet" href="{}">'.format(util.escape_html(url(location)))


def inline_js(s: str = None) -> Optional[str]:
    tid = threading.get_id()

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

    return router.url('/assets/{}/{}'.format(package_name, asset_path), add_lang_prefix=False)


def _check_npm_installation():
    """Check if the NPM is installed
    """
    if _run_process(['which', 'npm'], False).returncode != 0:
        raise RuntimeError('NPM executable is not found. Check https://docs.npmjs.com/getting-started/installing-node')


def npm_install(packages: Union[str, List[str]]):
    """Install NPM package(s)
    """
    _check_npm_installation()
    cwd = getcwd()

    try:
        # Node modules should be installed exactly to the root of the project to get things work
        chdir(reg.get('paths.root'))
        if isinstance(packages, str):
            packages = [packages]

        r = _run_process(['npm', 'install', '--no-save', '--no-audit', '--no-package-lock'] + packages)
        r.check_returncode()

    except subprocess.CalledProcessError:
        msg = 'Error while installing required NPM package(s): {}'.format(packages)
        raise RuntimeError(msg)

    finally:
        chdir(cwd)


def install_npm_deps(package_names: Union[str, List[str]]):
    """Install NPM packages required by locally installed plugins
    """
    is_dev_host = path.isdir(path.join(reg.get('paths.root'), 'npm_packages'))

    if isinstance(package_names, str):
        package_names = [package_names]

    # Build list of NPM packages required by plugins
    npm_pkgs_to_install = []
    for pkg_name in package_names:
        # Skip package if it does not provide package.json
        json_path = path.join(assets_src(pkg_name), 'package.json')
        if not path.exists(json_path):
            continue

        # Collect dependencies
        json = util.load_json(json_path)
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
    console.print_info(lang.t('assetman@installing_required_npm_packages'))

    root_dir = reg.get('paths.root')
    node_modules_subdir = path.join(path.join(root_dir, 'node_modules'), '@pytsite')
    dev_host_npm_packages_dir = path.join(root_dir, 'npm_packages')
    is_dev_host = path.isdir(dev_host_npm_packages_dir)

    makedirs(node_modules_subdir, 0o755, True)

    # Create symlinks in node_modules from npm_packages
    if is_dev_host:
        for name in listdir(dev_host_npm_packages_dir):
            src = path.join(dev_host_npm_packages_dir, name)
            if path.isdir(src):
                dst = path.join(node_modules_subdir, name)
                if not path.exists(dst):
                    symlink(src, dst)

    # Create symlinks in node_modules from registered packages which have package.json
    for pkg_name in _packages:
        src_dir = assets_src(pkg_name)
        if not path.exists(path.join(src_dir, 'package.json')):
            continue

        node_pkg_name = pkg_name.replace('plugins.', '').replace('_', '-').replace('.', '-')
        node_modules_pkg_dir = path.join(node_modules_subdir, node_pkg_name)
        if not path.exists(node_modules_pkg_dir):
            symlink(src_dir, node_modules_pkg_dir)

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
    for dep_pkg_name in package_info.requires_plugins(pkg_name):
        dep_pkg_name = 'plugins.' + dep_pkg_name
        if lang.is_package_registered(dep_pkg_name):
            build_translations(dep_pkg_name)

    output_file = path.join(assets_dst('assetman'), 'translations.json')

    # Prepare data structure
    if path.exists(output_file):
        data = util.load_json(output_file)
    else:
        data = {'langs': {}, 'translations': {}}

    # Update languages information
    data['langs'] = lang.langs()

    # Build translations structure
    for lang_code in lang.langs():
        if lang_code not in data['translations']:
            data['translations'][lang_code] = {}
        logger.info('Compiling translations for {} ({})'.format(pkg_name, lang_code))
        data['translations'][lang_code][pkg_name] = lang.get_package_translations(pkg_name, lang_code)

    # Create output directory
    output_dir = path.dirname(output_file)
    if not path.exists(output_dir):
        makedirs(output_dir, 0o755, True)

    # Write translations to teh file
    with open(output_file, 'wt', encoding='utf-8') as f:
        logger.debug("Writing translations into '{}'".format(output_file))
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
    if lang.is_package_registered(pkg_name):
        build_translations(pkg_name)

    # Building is possible only if 'webpack.config.js' exists
    webpack_config = path.join(src, 'webpack.config.js')
    if not path.exists(webpack_config):
        return

    # Clear destination directory
    if path.exists(dst):
        rmtree(dst)

    webpack_parts = []
    root_dir = reg.get('paths.root') + '/'
    for p in _packages.values():
        if path.exists(path.join(p[0], 'webpack.part.js')):
            webpack_parts.append(p[0].replace(root_dir, ''))

    # Run webpack
    console.print_info(lang.t('assetman@compiling_assets_for_package', {'package': pkg_name}))
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
    console.print_info(lang.t('assetman@compiling_assets'))

    assets_static_path = reg.get('paths.assets')
    node_modules_dir = path.join(reg.get('paths.root'), 'node_modules')
    node_modules_subdir = path.join(node_modules_dir, '@pytsite')

    if not path.isdir(node_modules_dir):
        raise FileNotFoundError("'{}' directory is not exists. Check your NPM installation.")

    if not path.isdir(node_modules_subdir):
        mkdir(node_modules_subdir, 0o755)

    if path.exists(assets_static_path):
        rmtree(assets_static_path)

    for pkg_name in _packages:
        build(pkg_name, debug, mode)


def on_split_location(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('assetman@split_location', handler, priority)


def _split_location(location: str) -> Tuple[str, str]:
    """Split asset path into package name and asset path
    """
    for r in events.fire('assetman@split_location', location=location):
        location = r

    package_name, assets_path = location.split('@')[:2] if '@' in location else ['app', location]

    return resolve_package(package_name), assets_path
