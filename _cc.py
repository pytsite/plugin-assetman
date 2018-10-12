"""PytSite Assetman Plugin Console Commands
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import console as _console, maintenance as _maintenance, lang as _lang, reg as _reg
from . import _api, _error

_DEV_MODE = _reg.get('debug', False)


class NpmInstall(_console.Command):
    """npm:install Console Command.
    """

    @property
    def name(self) -> str:
        """Get name of the command.
        """
        return 'npm:install'

    @property
    def description(self) -> str:
        """Get description of the command.
        """
        return 'assetman@npm_install_console_command_description'

    @property
    def signature(self) -> str:
        return '{} <PACKAGE>...'.format(super().signature)

    def exec(self):
        if not self.args:
            return

        try:
            _maintenance.enable()
            _console.print_info(_lang.t('assetman@installing_npm_packages', {'packages': ', '.join(self.args)}))
            _api.npm_install(self.args)
        except RuntimeError as e:
            raise _console.error.CommandExecutionError(e)
        finally:
            _maintenance.disable()


class Setup(_console.Command):
    """assetman:setup Console Command.
    """

    @property
    def name(self) -> str:
        """Get name of the command.
        """
        return 'assetman:setup'

    @property
    def description(self) -> str:
        """Get description of the command.
        """
        return 'assetman@assetman_setup_console_command_description'

    def exec(self):

        try:
            _maintenance.enable()
            _api.setup()
        finally:
            _maintenance.disable()


class Build(_console.Command):
    """assetman:build Console Command.
    """

    def __init__(self):
        super().__init__()

        self.define_option(_console.option.Bool('debug', default=_DEV_MODE))
        self.define_option(_console.option.Bool('no-maint'))

    @property
    def name(self) -> str:
        """Get name of the command.
        """
        return 'assetman:build'

    @property
    def description(self) -> str:
        """Get description of the command.
        """
        return 'assetman@assetman_build_console_command_description'

    def exec(self):
        """Execute The Command.
        """
        maint = not self.opt('no-maint')
        debug = self.opt('debug')

        try:
            if maint:
                _maintenance.enable()

            packages = self.args
            if packages:
                for package in packages:
                    _api.build(package, debug)
            else:
                _api.build_all(debug)

        except (RuntimeError, _error.PackageNotRegistered, _error.PackageAlreadyRegistered) as e:
            raise _console.error.CommandExecutionError(e)

        finally:
            if maint:
                _maintenance.disable()
