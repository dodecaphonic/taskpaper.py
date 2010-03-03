import os

__taskpaper_data_directory__ = "../data"

def get_data_path():
    """Retrieve Taskpaper's data path

    This path is by default <taskpaper_lib_path>/../data/ in trunk
    and /usr/share/teste in an installed version but this path
    is specified at installation time.
    """

    # get pathname absolute or relative
    if __taskpaper_data_directory__.startswith('/'):
        pathname = __taskpaper_data_directory__
    else:
        pathname = os.path.dirname(__file__) + '/' + __taskpaper_data_directory__

    abs_data_path = os.path.abspath(pathname)
    if os.path.exists(abs_data_path):
        return abs_data_path
    else:
        raise project_path_not_found
