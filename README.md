# PytSite Assets Manager Plugin


## Changelog


### 5.1.7 (2019-04-26)

Cleanup.


### 5.1.6 (2019-01-02)

Development environment Webpack's base config issue fixed.


### 5.1.5 (2018-10-31)

Building language translations fixed.


### 5.1.4 (2018-10-29)

Automatic app's package resources registration fixed.


### 5.1.3 (2018-10-28)

Webpack's configuration parts collecting issue fixed.


### 5.1.2 (2018-10-24)

Webpack's mode setting issue fixed.


### 5.1.1 (2018-10-23)

Typo fixed.


### 5.1 (2018-10-22)

Webpack's `circular-dependency-plugin` added.


### 5.0.1 (2018-10-22)

`inline_js()` fixed.


### 5.0 (2018-10-22)

- New `assetman:build` console command options: `mode` and `watch`.
- Translations building refactored.
- `lang` browser global replaced with module-exported property.
- React and Babel are required dependencies now.


### 4.1 (2018-10-12)

- Missing functions exposed to the public API.
- Plugin installation hooks fixed.


### 4.0 (2018-10-12)

- `js_tag()` renamed to `js()`, `css_tag()` renamed to `css()`.
- API functions removed: `preload()`, `add_inline_js()`, `js_tags()`,
  `css_tags()`.
- `--debug` option behavior of console command `assetman:build` fixed.


### 3.0 (2018-10-04)

- Gulp replaced with Webpack.
- Automatic plugins assets directories registration added,
- API functions removed: `library()`, `urls()`, `register_global()`,
  `t_copy()`, `t_copy_static()`, `t_less()`, `t_scss()`, `t_js()`,
  `t_css()`, `js_module()`, `npm_update()`.
- `get_src_dir_path()` renamed to `assets_src()`, `get_dst_dir_path()`
  renamed to `assets_dst()`.


### 2.5 (2018-08-31)

New JavaScript methods: `url()`, `parseQueryString()`.


### 2.4.4 (2018-08-30)

Babelified JS compilation fixed.


### 2.4.3 (2018-08-30)

Babel installation issue fixed.


### 2.4.2 (2018-08-11)

Usage of Python 3.7 reserved word `async` fixed.


### 2.4.1 (2018-08-10)

Typo fixed.


### 2.4 (2018-07-29)

`callback` argument removed from `load*` JS functions.


### 2.3 (2018-07-16)

- `String.prototype.startsWith` JS polyfill added.
- `source_maps` argument removed from `t_js()`.


### 2.2 (2018-07-09)

- New console commands added: `assetman:setup`, `npm:install`,
  `npm:update`.
- `t_browserify()` API function removed.
- List of required NPM packages updated.
- NPM packages installation errors reporting fixed.


### 2.1 (2018-07-02)

Support of SCSS added.


### 2.0 (2018-06-26)

- New API functions added: `js_tag`, `css_tag`.
- API functions renamed: `dump_js()` to `js_tags()`, `dump_css()` to
  `css_tags()`, `add_inline()` to `add_inline_js()`, `dump_inline()` to
  `inline_js()`.
- New `tpl`'s globals added: `css_tag()`, `js_tag()`.
- `tpl`'s globals renamed: `css_links()` to `css_tags()`, `js_links()`
  to `js_tags()`, `js_head_links()` to `js_head_tags()`.


### 1.8 (2018-06-22)

Support of strings as second argument in `library()`.


### 1.7 (2018-06-13)

- `remove()` API function removed.
- `path_prefix`, `exclude_path_prefix` argument removed from
  `preload()`.


### 1.6 (2018-05-30)

Support of PytSite-7.23.


### 1.5.2 (2018-05-27)

Nonworking minification Gulp's function fixed.


### 1.5.1 (2018-05-22)

Clean installation error fixed.


### 1.5 (2018-05-21)

Asset libraries resolving in JS code added.


### 1.4.1 (2018-05-14)

Installation hook fixed.


### 1.4 (2018-05-14)

- Package aliases resolving in JS code added.
- New JS API functions: `load()` and `definePackageAlias()`.


### 1.3.7 (2018-05-06)

Unnecessary call of `build_all()` during plugin installation removed.


### 1.3.6 (2018-05-02)

Fix to support version 10 of NPM.


### 1.3.5 (2018-02-14)

Logging verbosity decreased.


### 1.3.4 (2018-02-11)

File renamed.


### 1.3.3 (2018-02-11)

Bugfix of support for PytSite-7.8.


### 1.3.2 (2018-02-10)

Support for PytSite-7.8.


### 1.3.1 (2018-02-07)

Support for PytSite-7.7.


### 1.3 (2018-01-29)

`error.NoTasksDefined` removed.


### 1.2.15 (2018-01-28)

Init code fixed.


### 1.2.14 (2018-01-03)

Fixed unnecessary translations compilation of aliased packages.


### 1.2.13 (2017-12-22)

Removed automatic assets and translations compilation on PytSite update
event.


### 1.2.12 (2017-12-21)

Init code fixed.


### 1.2.11 (2017-12-21)

Init code fixed.


### 1.2.10 (2017-12-21)

Init code fixed.


### 1.2.9 (2017-12-20)

Improper import fixed.


### 1.2.8 (2017-12-20)

Init fixed.


### 1.2.7 (2017-12-20)

Init fixed.


### 1.2.6 (2017-12-20)

Init and installation fixed.


### 1.2.5 (2017-12-19)

Init and installation fixed.


### 1.2.4 (2017-12-19)

Init and installation fixed.


### 1.2.3 (2017-12-18)

Location string splitting fixed.


### 1.2.2 (2017-12-15)

Installation code fixed.


### 1.2.1 (2017-12-13)

Events names fixed.


### 1.2 (2017-12-13)

Support for PytSite-7.0.


### 1.1 (2017-12-02)

Added plugman's hooks.


### 1.0 (2017-11-24)

First release.
