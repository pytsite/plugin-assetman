"""PytSite Assetman Plugin Console Commands
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import console, maintenance, lang, reg
from . import _api, _error

_DEV_MODE = reg.get('debug', False)


class NpmInstall(console.Command):
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
            maintenance.enable()
            console.print_info(lang.t('assetman@installing_npm_packages', {'packages': ', '.join(self.args)}))
            _api.npm_install(self.args)
        except RuntimeError as e:
            raise console.error.CommandExecutionError(e)
        finally:
            maintenance.disable()


class Setup(console.Command):
    """assetman:setup Console Command
    """

    @property
    def name(self) -> str:
        """Get name of the command
        """
        return 'assetman:setup'

    @property
    def description(self) -> str:
        """Get description of the command
        """
        return 'assetman@assetman_setup_console_command_description'

    def exec(self):

        try:
            maintenance.enable()
            _api.setup()
        finally:
            maintenance.disable()


class Build(console.Command):
    """assetman:build Console Command
    """

    def __init__(self):
        super().__init__()

        self.define_option(console.option.Str('mode', default='development' if _DEV_MODE else 'production'))
        self.define_option(console.option.Bool('debug', default=_DEV_MODE))
        self.define_option(console.option.Bool('watch'))
        self.define_option(console.option.Bool('no-maint'))

    @property
    def name(self) -> str:
        """Get name of the command
        """
        return 'assetman:build'

    @property
    def description(self) -> str:
        """Get description of the command
        """
        return 'assetman@assetman_build_console_command_description'

    def exec(self):
        """Execute The Command.
        """
        maint = not self.opt('no-maint')
        debug = self.opt('debug')
        mode = self.opt('mode')
        watch = self.opt('watch')

        if watch and not self.args:
            raise console.error.CommandExecutionError('--watch option must be used only with package name')

        try:
            if maint and not watch:
                maintenance.enable()

            packages = self.args
            if packages:
                if len(packages) > 1:
                    watch = False

                for package in packages:
                    _api.build(package, debug, mode, watch)
            else:
                _api.build_all(debug, mode)

        except (RuntimeError, _error.PackageNotRegistered, _error.PackageAlreadyRegistered) as e:
            raise console.error.CommandExecutionError(e)

        except KeyboardInterrupt:
            console.print_info('')

        finally:
            if maint and not watch:
                maintenance.disable()
