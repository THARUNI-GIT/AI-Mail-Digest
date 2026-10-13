
import unittest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TestMailDigestUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")

        cls.driver = webdriver.Chrome(options=options)
        cls.driver.get("http://localhost:8501")

        cls.wait = WebDriverWait(cls.driver, 30)

        # Wait until Streamlit finishes rendering its main app container.
        cls.wait.until(
            lambda driver: driver.find_elements(
                By.CSS_SELECTOR, "[data-testid='stAppViewContainer']"
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_app_page_loads(self):
        self.assertIn("localhost:8501", self.driver.current_url)

    def test_streamlit_app_container_is_visible(self):
        app_container = self.wait.until(
            lambda driver: driver.find_element(
                By.CSS_SELECTOR, "[data-testid='stAppViewContainer']"
            )
        )
        self.assertTrue(app_container.is_displayed())


if __name__ == "__main__":
    unittest.main(verbosity=2)
