'''
Default tasks Module.
'''

from fabric.api import run as _run, hide, task
from fabric.context_managers import shell_env
import boss.constants as constants
from .util import warn_deprecated, halt, remote_info
from .api import git, notif, shell, npm, systemctl, runner
from .config import fallback_branch, get_service, get_stage_config, get as get_config

stage = shell.get_stage()


@task
def check():
    ''' Check the current remote branch and the last commit. '''
    with hide('running'):
        # Show the current branch
        remote_branch = git.remote_branch()
        _run('echo "Branch: %s"' % remote_branch)
        # Show the last commit
        git.show_last_commit()


@task
def deploy(branch=None):
    ''' The deploy task. '''
    branch = branch or fallback_branch(stage)
    notif.send(notif.DEPLOYMENT_STARTED, {
        'user': shell.get_user(),
        'branch': branch,
        'stage': stage
    })

    # Get the latest code from the repository
    sync(branch)
    install_dependencies()

    # Building the app
    build(stage)
    reload_service()

    notif.send(notif.DEPLOYMENT_FINISHED, {
        'branch': branch,
        'stage': stage
    })

    remote_info('Deployment Completed')


def reload_service():
    ''' Reload the service after deployment. '''
    service = get_service()

    if service:
        # TODO: Remove this in future release (BC Break).
        # Enable and Restart the service if service is provided
        warn_deprecated(
            'Reloading service using systemctl is deprecated and ' +
            'will be removed in major future release. ' +
            'Define `{}` script in your config instead.'.format(
                constants.SCRIPT_RELOAD)
        )
        systemctl.enable(service)
        systemctl.restart(service)
        systemctl.status(service)
    else:
        # Trigger reload script if it's defined.
        runner.run_script_safely(constants.SCRIPT_RELOAD)
        runner.run_script_safely(constants.SCRIPT_STATUS_CHECK)


def install_dependencies():
    ''' Install dependencies. '''
    # Trigger install script.
    runner.run_script_safely(constants.SCRIPT_INSTALL)

    # If install script is not defined,
    # Fallback to old `npm install` for backwards compatilibity.
    # TODO: Remove this in the next release (BC break).
    if not runner.is_script_defined(constants.SCRIPT_INSTALL):
        warn_deprecated(
            'Define `{}` script explicitly if you need to '.format(constants.SCRIPT_INSTALL) +
            'install dependencies on deployment. ' +
            'In future releases `npm install` won\'t be triggered on deployment.'
        )
        npm.install()


@task
def sync(branch=None):
    ''' Sync the changes on the branch with the remote (origin). '''
    git.fetch()
    branch = branch or git.remote_branch()
    remote_info('Checking out to %s branch' % branch)
    git.checkout(branch, True)
    remote_info('Syncing the latest changes of the %s branch' % branch)
    git.sync(branch)


@task
def build(stage_name=None):
    ''' Build the application. '''
    with shell_env(STAGE=(stage_name or stage)):
        # Trigger the build script.
        runner.run_script_safely(constants.SCRIPT_BUILD)

        # Fallback to old npm run build way, if the build script is not defined.
        # TODO: Remove this (BC Break).
        if not runner.is_script_defined(constants.SCRIPT_BUILD):
            warn_deprecated(
                'Define `{}` script explicitly if you need to '.format(constants.SCRIPT_BUILD) +
                'build. ' +
                'In future releases `npm run build` won\'t be triggered on deployment.'
            )
            npm.run('build')


@task
def stop():
    ''' Stop the systemctl service. '''
    runner.run_script_safely(constants.SCRIPT_STOP)

    # Fallback to old systemctl stop, if the stop script is not defined.
    # TODO: Remove this (BC Break).
    if not runner.is_script_defined(constants.SCRIPT_STOP):
        # Deprecate everything that is tightly coupled to systemd
        # as they are subject to change in the major future release.
        warn_deprecated(
            'The `stop` using systemctl service task is deprecated. ' +
            'Define `{}` script instead.'.format(constants.SCRIPT_STOP)
        )
        systemctl.stop(get_service())


@task
def restart():
    ''' Restart the service. '''
    runner.run_script_safely(constants.SCRIPT_RELOAD)

    # Fallback to old systemctl way, if the script is not defined.
    # TODO: Remove this (BC Break).
    if not runner.is_script_defined(constants.SCRIPT_RELOAD):
        # Deprecate everything that is tightly coupled to systemd
        # as they are subject to change in the major future release.
        warn_deprecated(
            'The `restart` using systemctl service task is deprecated. ' +
            'Define `{}` script instead.'.format(constants.SCRIPT_RELOAD)
        )
        systemctl.restart(get_service())


@task
def status():
    ''' Get the status of the service. '''
    runner.run_script_safely(constants.SCRIPT_STATUS_CHECK)

    # Fallback to old systemctl way, if the script is not defined.
    # TODO: Remove this (BC Break).
    if not runner.is_script_defined(constants.SCRIPT_STATUS_CHECK):
        warn_deprecated(
            'The `status` using systemctl service task is deprecated. ' +
            'Define `{}` script instead.'.format(constants.SCRIPT_STATUS_CHECK)
        )
        systemctl.status(get_service())


@task
def logs():
    ''' Tail the logs. '''
    # Tail the logs from journalctl if
    # systemctl service is configured
    # TODO: Remove this (BC Break)
    if get_service():
        warn_deprecated(
            'Using journalctl to tail the logs from ' +
            'configured service is deprecated. ' +
            'You\'ll need to provide the config explicitly for logging.'
        )
        _run('sudo journalctl -f -u %s' % get_service())
        return

    # Get the logging config
    stage_specific_logging = get_stage_config(stage).get('logging')
    logging_config = stage_specific_logging or get_config().get('logging')

    # If log files are configured tail them.
    if logging_config and logging_config.get('files'):
        # Tail the logs from log files
        log_paths = ' '.join(logging_config.get('files'))
        _run('tail -f ' + log_paths)
        return

    # If logs script is defined, run it
    runner.run_script_safely(constants.SCRIPT_LOGS)


@task
def run(script):
    ''' Run a custom script. '''
    # Run a custom script defined in the config.
    try:
        runner.run_script(script)
    except RuntimeError, e:
        halt(str(e))


__all__ = ['deploy', 'check', 'sync', 'build',
           'stop', 'restart', 'status', 'logs', 'run']
