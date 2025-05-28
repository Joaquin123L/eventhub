from django.utils import timezone
from app.models import User, Event, Ticket, DiscountCode
from app.test.test_e2e.base import BaseE2ETest
from django.urls import reverse
import datetime
from django.test.client import Client
from django.utils.timezone import now, timedelta
import os


class TicketDiscountE2ETest(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        self.regular_user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        event_date = timezone.make_aware(datetime.datetime(2025, 6, 15, 18, 0))
        self.event = Event.objects.create(
            title="Evento con Descuento",
            description="Evento para probar códigos de descuento",
            scheduled_at=event_date,
            organizer=self.organizer,
            capacity=100
        )

        # Crear código de descuento válido
        self.valid_discount = DiscountCode.objects.create(
            code="DESCUENTO10",
            discount_percentage=10,
            event=self.event,
            valid_from=now() - timedelta(days=1),
            valid_until=now() + timedelta(days=30),
            active=True
        )

        # Crear código de descuento expirado
        self.expired_discount = DiscountCode.objects.create(
            code="EXPIRADO",
            discount_percentage=15,
            event=self.event,
            valid_from=now() - timedelta(days=10),
            valid_until=now() - timedelta(days=1),
            active=True
        )

        # Crear código de descuento inactivo
        self.inactive_discount = DiscountCode.objects.create(
            code="INACTIVO",
            discount_percentage=20,
            event=self.event,
            valid_from=now() - timedelta(days=1),
            valid_until=now() + timedelta(days=30),
            active=False
        )

    def test_aplicar_codigo_descuento_valido(self):
        """Test que verifica la aplicación correcta de un código de descuento válido"""
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event.pk}")
        self.page.wait_for_load_state("networkidle")

        # Llenar datos básicos del formulario
        self.page.fill("input[name='card_name']", "Juan Pérez")
        self.page.fill("input[name='card_number']", "4242424242424242")
        self.page.fill("input[name='card_expiry']", "12/30")
        self.page.fill("input[name='card_cvv']", "123")
        self.page.check("input[name='accept_terms']")
        self.page.select_option("select[name='type']", "general")
        self.page.fill("#quantity", "1")

        # Aplicar código de descuento
        discount_input = self.page.locator("input[name='discount_code']")
        discount_input.fill("DESCUENTO10")

        # Hacer click en validar descuento
        apply_button = self.page.wait_for_selector("#validate-discount", timeout=10000)
        apply_button.click() # type: ignore

        # Esperar feedback visible
        self.page.wait_for_selector("#discount-feedback .alert small", timeout=10000)

        # Verificar mensaje de éxito
        success_message = self.page.locator("#discount-feedback .alert small")
        try:
            assert "10.00%" in success_message.inner_text() or "DESCUENTO10" in success_message.inner_text()
        except AssertionError:
            print("Mensaje recibido:", success_message.inner_text())
            raise

        # Completar la compra
        self.page.click("#submit-btn")

        # Esperar redirección correcta
        self.page.wait_for_url("**/satisfaction_survey/**", timeout=10000)
        self.page.wait_for_load_state("networkidle")  # Asegura que todo haya cargado