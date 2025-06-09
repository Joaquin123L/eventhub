import datetime

from django.utils import timezone

from app.models import Event, User
from app.test.test_e2e.base import BaseE2ETest


class ComprarTicketE2ETest(BaseE2ETest):

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

        event_date1 = timezone.make_aware(datetime.datetime(2025, 2, 10, 10, 10))
        self.event = Event.objects.create(
            title="Evento de prueba 1",
            description="Descripción del evento 1",
            scheduled_at=event_date1,
            organizer=self.organizer,
        )

class PruebaTicketE2E(ComprarTicketE2ETest):

    def test_no_puede_comprar_mas_de_4_tickets(self):
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event.pk}")
        quantity_input = self.page.locator("#quantity")
        quantity_input.fill("5")

        assert quantity_input.evaluate("el => el.validity.rangeOverflow"), \
        "El campo no muestra error por exceder el máximo."

        validation_message = quantity_input.evaluate("el => el.validationMessage")
        print("Mensaje de validación:", validation_message)

        assert (
        "less than or equal to" in validation_message
        or "menor o igual a" in validation_message
        ), "No se muestra el mensaje esperado al exceder el máximo permitido."

        form_valid = self.page.locator("#payment-form").evaluate("form => form.checkValidity()")
        assert not form_valid, "El formulario debería ser inválido si se ingresan más de 4 entradas."

    #Agrego test para verificar que si el usuario quiere comprar mas entradas que las que hay disponibles aparece un mensaje de error 
    def test_no_puede_comprar_mas_de_entradas_disponibles(self):
        # Crear evento con 1 entrada disponible
        self.event.capacity = 1
        self.event.save()

        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event.pk}")

        # Llenar datos del formulario
        self.page.fill("input[name='card_name']", "Juan Pérez")
        self.page.fill("input[name='card_number']", "4242424242424242")
        self.page.fill("input[name='card_expiry']", "12/30")
        self.page.fill("input[name='card_cvv']", "123")
        self.page.check("input[name='accept_terms']")
        self.page.select_option("select[name='type']", "general")
        self.page.fill("#quantity", "2")  # más de la capacidad

        # Enviar formulario
        self.page.click("#submit-btn")


        # Esperar al mensaje de error
        error_element = self.page.locator(".alert-danger") 
        error_element.wait_for(timeout=10000)

        # Validar mensaje
        assert error_element.is_visible(), "El mensaje de error no está visible"
        expected_text = f"Solo quedan {self.event.capacity} entradas"
        assert expected_text in error_element.inner_text(), f"Mensaje incorrecto: {error_element.inner_text()}"



