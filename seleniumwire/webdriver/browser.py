from selenium.webdriver import Firefox as _Firefox

from .request import InspectRequestsMixin


class Firefox(InspectRequestsMixin, _Firefox):
    pass
