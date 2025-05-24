from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Event, Ticket, User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum


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

class PruebaTicketUnit(TicketLimitTest):

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

    
    # agrego test para comprobar la cantidad de entradas que quedan para un ticket, por ejemplo creo un evento con 10 entradas y luego creo un ticket con 2 entradas, entonces la cantidad de entradas que quedan para ese ticket es 8
    def test_cantidad_entradas_disponibles(self):
        #hace la creacion del evento con capacity = 10
        event = Event.objects.create(
            title="Evento test",
            description="Descripción de prueba",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.organizer,
            capacity=10
        )
        #hace la creacion del ticket con quantity = 2
        ticket = Ticket.objects.create(
            ticket_code="ABC1",
            quantity=2,
            user=self.user,
            event=event
        )
        # Calcula las entradas usadas (sumando todos los tickets del evento)
        entradas_usadas = Ticket.objects.filter(event=event).aggregate(total=Sum('quantity'))['total'] or 0

        # Calcula las entradas disponibles
        capacidad_evento = event.capacity if event.capacity is not None else 0
        entradas_disponibles = capacidad_evento - entradas_usadas
        self.assertEqual(entradas_disponibles, 8)
