import typing


def get_environ_proxies(url, no_proxy=None):
    return {

    }


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if isinstance(value, typing.Mapping):
        value = value.items()

    return list(value)


def merge_setting(request_setting: typing.Mapping, session_setting):
    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting
    if not (
            isinstance(session_setting, typing.Mapping) and isinstance(request_setting, typing.Mapping)
    ):
        return request_setting
    merged_setting = dict(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]

    return merged_setting

