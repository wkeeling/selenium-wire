from selenium.webdriver import Firefox as _Firefox

from .request import RequestMixin


class Firefox(RequestMixin, _Firefox):
    pass
