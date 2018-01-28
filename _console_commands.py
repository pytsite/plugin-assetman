"""PytSite Assetman Plugin Console Commands
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import console as _console, maintenance as _maintenance
from . import _api, _error


class Build(_console.Command):
    """assetman:build Console Command.
    """

    def __init__(self):
        super().__init__()

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

        try:
            if maint:
                _maintenance.enable()

            packages = self.args
            if packages:
                for package in packages:
                    _api.build(package)
            else:
                _api.build_all()

            # Compile translations
            _api.build_translations()

        except (RuntimeError, _error.PackageNotRegistered, _error.PackageAlreadyRegistered) as e:
            raise _console.error.Error(e)

        finally:
            if maint:
                _maintenance.disable()
