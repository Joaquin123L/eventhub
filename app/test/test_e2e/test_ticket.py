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

   def test_puede_comprar_hasta_4_tickets(self):
    self.login_user("usuario", "password123")
    
    # Ir a la página de compra
    self.page.goto(f"{self.live_server_url}/ticket_compra/{self.event.pk}")

    # Completar el formulario
    self.page.locator('#quantity').fill("4")
    self.page.locator('#type').select_option("general")
    self.page.locator("#card_number").fill("4111111111111111")
    self.page.locator("#card_expiry").fill("12/25")
    self.page.locator("#card_cvv").fill("123")
    self.page.locator("#card_name").fill("Test User")
    self.page.locator("#accept_terms").check()

    # Enviar el formulario
    self.page.click("button[type='submit']")

    self.login_user("usuario", "password123")
    # Ir a Mis tickets (asegurate que el usuario sigue logueado)
    mis_tickets_url = f"{self.live_server_url}{reverse('Mis_tickets')}"
    self.page.goto(mis_tickets_url)
    print("URL en mis_tickets:", self.page.url)

    # Verificar la alerta
    alert = self.page.locator(".alert.alert-danger")
    if not alert.is_visible():
        print("No se encontró la alerta. HTML completo:")
        print(self.page.content())
    assert alert.is_visible(), "No se encontró un mensaje de alerta tras la compra."