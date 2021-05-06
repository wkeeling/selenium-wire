try:
    import undetected_chromedriver as uc
except ImportError as e:
    raise ImportError(
        'undetected_chromedriver not found. '
        'Install it with `pip install undetected_chromedriver`.'
    ) from e

from seleniumwire.webdriver import Chrome

uc._Chrome = Chrome
Chrome = uc.Chrome
ChromeOptions = uc.ChromeOptions  # noqa: F811
