''' Tests for boss.api.deployment.buildman module. '''

from mock import patch
from boss.api.deployment import buildman


@patch('boss.api.deployment.buildman.get_stage_config')
def test_resolve_local_build_dir_when_build_dir_is_configured(gsc_mock):
    '''
    Test resolve_local_build_dir() returns configured value if build_dir is configured.
    '''

    test_build_dir = 'my-build-directory'
    gsc_mock.return_value = {
        'deployment': {
            'build_dir': test_build_dir
        }
    }

    assert buildman.resolve_local_build_dir() == test_build_dir


@patch('os.path.exists')
@patch('boss.api.deployment.buildman.get_stage_config')
def test_resolve_local_build_dir_when_build_dir_is_none(gsc_mock, exists_mock):
    '''
    Test resolve_local_build_dir() returns one of the default
    build directories, if build_dir is not provided and
    fallback directories don't exist either.
    '''
    exists_mock.return_value = False
    gsc_mock.return_value = {
        'deployment': {
            'build_dir': None
        }
    }

    result = buildman.resolve_local_build_dir()

    assert result in buildman.LOCAL_BUILD_DIRECTORIES


@patch('os.path.exists')
@patch('boss.api.deployment.buildman.get_stage_config')
def test_resolve_local_build_dir_when_build_dir_none_with_fallback_directory(gsc_mock, exists_mock):
    '''
    Test resolve_local_build_dir(), when build_dir is not configured,
    but one of the fallback directories exist locally. It should return,
    the existing directory name.
    '''
    exists_mock.return_value = True
    gsc_mock.return_value = {
        'deployment': {
            'build_dir': None
        }

    }
    result = buildman.resolve_local_build_dir()

    assert result in buildman.LOCAL_BUILD_DIRECTORIES[0]


@patch('boss.api.deployment.buildman.load_history')
@patch('boss.api.deployment.buildman.git.last_commit')
def test_is_up_to_date_returns_true(glc_m, lh_m):
    ''' Test is_up_to_date(). '''
    glc_m.return_value = '5ff8648'
    lh_m.return_value = {
        'builds': [
            {'id': '1', 'commit': '1232333'},
            {'id': '2', 'commit': '5ff8648'}
        ],
        'current': '2'
    }

    assert buildman.is_remote_up_to_date()


@patch('boss.api.deployment.buildman.load_history')
@patch('boss.api.deployment.buildman.git.last_commit')
def test_is_up_to_date_returns_false(glc_m, lh_m):
    ''' Test is_up_to_date(). '''
    glc_m.return_value = '5ff8648'
    lh_m.return_value = {
        'builds': [
            {'id': '1', 'commit': '1255452'},
            {'id': '2', 'commit': '1232333'}
        ],
        'current': '2'
    }

    assert not buildman.is_remote_up_to_date()


def test_get_prev_build_info():
    ''' Test get_prev_build_info() returns previous build information. '''
    history = {
        'builds': [
            {'id': 'abc0', 'commit': '1255452', 'path': '/home/kabir/builds/test1'},
            {'id': 'abc1', 'commit': '1232333', 'path': '/home/kabir/builds/test2'}
        ],
        'current': 'abc0'
    }

    prev_build = buildman.get_prev_build_info(history)

    assert prev_build == history['builds'][1]


def test_get_prev_build_info_if_no_previous_build():
    ''' Test get_prev_build_info() returns None if previous build does not exist. '''
    history = {
        'builds': [
            {'id': 'abc0', 'commit': '1255452', 'path': '/home/kabir/builds/test1'},
            {'id': 'abc1', 'commit': '1232333', 'path': '/home/kabir/builds/test2'}
        ],
        'current': 'abc1'
    }

    prev_build = buildman.get_prev_build_info(history)

    assert prev_build is None


def test_get_prev_build_info_if_empty_history():
    ''' Test get_prev_build_info() returns None if history is empty. '''
    history = {}
    prev_build = buildman.get_prev_build_info(history)

    assert prev_build is None


def test_get_prev_build_info_if_empty_builds_or_current():
    '''
    Test get_prev_build_info() returns None if
    build history is empty or current is None.
    '''
    history = {
        'builds': [],
        'current': None
    }
    prev_build = buildman.get_prev_build_info(history)

    assert prev_build is None
