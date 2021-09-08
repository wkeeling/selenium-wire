try:
    import undetected_chromedriver as uc  # type: ignore
except ImportError as e:
    raise ImportError(
        'undetected_chromedriver not found. ' 'Install it with `pip install undetected_chromedriver`.'
    ) from e

from seleniumwire.webdriver import Chrome

uc._Chrome = Chrome
Chrome = uc.Chrome  # type: ignore
ChromeOptions = uc.ChromeOptions  # noqa: F811
