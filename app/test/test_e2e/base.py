import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Browser, sync_playwright

from app.models import User

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
playwright = sync_playwright().start()
headless = os.environ.get("HEADLESS", 1) == 1
slow_mo = os.environ.get("SLOW_MO", 0)


class BaseE2ETest(StaticLiveServerTestCase):
    """Clase base con la configuración común para todos los tests E2E"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser: Browser = playwright.chromium.launch(
            headless=headless, slow_mo=int(slow_mo)
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.browser.close()

    def setUp(self):
        # Crear un contexto y página de Playwright
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def tearDown(self):
        # Cerrar la página después de cada test
        self.page.close()

    def create_test_user(self, is_organizer=False):
        """Crea un usuario de prueba en la base de datos"""
        return User.objects.create_user(
            username="usuario_test",
            email="test@example.com",
            password="password123",
            is_organizer=is_organizer,
        )

    def login_user(self, username, password):
        """Método auxiliar para iniciar sesión"""
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.get_by_label("Usuario").fill(username)
        self.page.get_by_label("Contraseña").fill(password)
        self.page.click("button[type='submit']")
