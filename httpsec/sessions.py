import os
from httpsec.poolmanager import HttpManager
from httpsec.utils import get_environ_proxies, merge_setting


class Session(object):
    def __init__(self):
        """
            管理会话
        """
        self.proxies = {}
        self.trust_env = True
        self.verify = True
        self.cert = False
        # 管理连接池
        self.adapters = HttpManager()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        """
        Check the environment and merge it with some settings.

        :rtype: dict
        """
        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            no_proxy = proxies.get('no_proxy') if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            for (k, v) in env_proxies.items():
                proxies.setdefault(k, v)

            # Look for requests environment configuration and be compatible
            # with cURL.
            if verify is True or verify is None:
                verify = (os.environ.get('REQUESTS_CA_BUNDLE') or
                          os.environ.get('CURL_CA_BUNDLE'))

        # Merge all the kwargs.
        proxies = merge_setting(proxies, self.proxies)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        return {'verify': verify, 'proxies': proxies, 'stream': stream,
                'cert': cert}

    def request(self, method, url,
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=True, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None):

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            url, proxies, stream, verify, cert
        )
        # Send the request.
        send_kwargs = {
            'timeout': timeout,
            'allow_redirects': allow_redirects,
        }
        send_kwargs.update(settings)
        return self.adapters.urlopen(method, url, **send_kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Closes all adapters and as such the session"""
        self.adapters.clear()


def session():
    return Session()
