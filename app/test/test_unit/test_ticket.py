from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Event, Ticket, User
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


class TicketLimitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="comprador", password="test123")
        self.organizer = User.objects.create_user(username="organizer", password="testpass", is_organizer=True)

        self.event = Event.objects.create(
            title="Evento test",
            description="Descripción de prueba",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.organizer
        )

    def entradas_totales(self):
        """Suma la cantidad total de entradas que el usuario compró para el evento"""
        return sum(t.quantity for t in Ticket.objects.filter(user=self.user, event=self.event))

    def test_puede_comprar_hasta_4(self):
        """Debe permitir comprar si la suma de entradas es menor a 4"""
        Ticket.objects.create(ticket_code="ABC1", quantity=2, user=self.user, event=self.event)
        Ticket.objects.create(ticket_code="ABC2", quantity=1, user=self.user, event=self.event)

        total = self.entradas_totales()
        self.assertEqual(total, 3)

        puede_comprar = (total + 1) <= 4  # ¿podría comprar 1 entrada más?
        self.assertTrue(puede_comprar)

    def test_no_puede_comprar_si_supera_4(self):
        """Debe rechazar si al sumar la cantidad nueva se supera el máximo"""
        Ticket.objects.create(ticket_code="ABC3", quantity=2, user=self.user, event=self.event)
        Ticket.objects.create(ticket_code="ABC4", quantity=2, user=self.user, event=self.event)

        total = self.entradas_totales()
        self.assertEqual(total, 4)

        puede_comprar = (total + 1) <= 4  # ¿podría comprar una más?
        self.assertFalse(puede_comprar)

    def test_no_puede_comprar_si_ya_superó_4(self):
        """Caso extremo: ya tiene más de 4 entradas"""
        Ticket.objects.create(ticket_code="ABC5", quantity=5, user=self.user, event=self.event)

        total = self.entradas_totales()
        self.assertEqual(total, 5)

        puede_comprar = (total + 1) <= 4
        self.assertFalse(puede_comprar)
