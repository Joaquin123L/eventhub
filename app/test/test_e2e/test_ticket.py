from django.utils import timezone
from app.models import User, Event, Ticket
from app.test.test_e2e.base import BaseE2ETest
from django.urls import reverse
import datetime
from django.test.client import Client
import os


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
