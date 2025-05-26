from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import datetime
from django.db.models import Sum
from app.models import User, Event, Ticket


class CompraTicketLimiteTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
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
            capacity=6,
        )
        self.event2 = Event.objects.create(
            title="Evento test",
            description="Descripción de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            capacity=3
        )
        self.client = Client()
        self.client.login(username="usuario", password="password123")

        self.ticket_url = reverse("ticket_compra", args=[self.event.pk])
        self.ticket_url2 = reverse("ticket_compra", args=[self.event2.pk])

    def _get_payment_data(self):
        # Datos de pago mínimos para la simulación
        return {
            "card_number": "4111111111111111",
            "card_expiry": "12/30",
            "card_cvv": "123",
            "card_name": "Test User",
        }

    
class PruebaTicketInt(CompraTicketLimiteTest):

    def test_puede_comprar_hasta_4_tickets(self):
        post_data_1 = {
            "quantity": 2,
            "ticket_code": "CODE789",
            "type": "general",
            **self._get_payment_data()
        }
        response_1 = self.client.post(self.ticket_url, post_data_1)
        if response_1.status_code != 302:
            print("Respuesta compra 1:", response_1.status_code)
            print(response_1.content.decode())
        self.assertEqual(response_1.status_code, 302)

        total_tickets = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 2)

        post_data_2 = {
            "quantity": 2,
            "ticket_code": "CODE987",
            "type": "general",
            **self._get_payment_data()
        }
        response_2 = self.client.post(self.ticket_url, post_data_2)
        if response_2.status_code != 302:
            print("Respuesta compra 2:", response_2.status_code)
            print(response_2.content.decode())
        self.assertEqual(response_2.status_code, 302)

        total_tickets = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 4)


    def test_no_puede_comprar_mas_de_4_tickets(self):
        post_data_1 = {
        "quantity": 3,
        "ticket_code": "CODE123",
        "type": "general",
        **self._get_payment_data()
    }
        response_1 = self.client.post(self.ticket_url, post_data_1)
        self.assertEqual(response_1.status_code, 302)  # Redirige al comprar bien

        total_tickets = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 3)

        post_data_2 = {
        "quantity": 2,
        "ticket_code": "CODE456",
        "type": "general",
        **self._get_payment_data()
        }
        response_2 = self.client.post(self.ticket_url, post_data_2)
        self.assertEqual(response_2.status_code, 200)  # No redirige porque excede límite

        total_tickets = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 3)  # No aumentó


    #Agrego test para validar que no se pueda comprar mas entradas de la cantidad de entradas disponibles
    def test_no_puede_comprar_mas_de_entradas_disponibles(self):
        # Crea un ticket con 3 entradas
        Ticket.objects.create(
            ticket_code="CODE123",
            quantity=3,
            user=self.user,
            event=self.event2
        )

        # Intenta comprar 1 entrada más
        post_data = {
            "quantity": 1,
            "ticket_code": "CODE456",
            "type": "general",
            **self._get_payment_data()
        }
        response = self.client.post(self.ticket_url2, post_data)
        self.assertEqual(response.status_code, 200)  # No redirige porque excede límite

        total_tickets = Ticket.objects.filter(user=self.user, event=self.event2).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 3) 
