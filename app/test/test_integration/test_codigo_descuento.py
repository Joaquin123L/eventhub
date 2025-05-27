import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from app.models import User,Event, Ticket, DiscountCode

class TicketPurchaseWithDiscountIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear organizador
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear usuario comprador
        self.buyer = User.objects.create_user(
            username="comprador_test",
            email="comprador@example.com",
            password="password123"
        )

        # Crear evento
        self.event = Event.objects.create(
            title="Evento con Descuentos",
            description="Evento para probar códigos de descuento",
            scheduled_at=timezone.now() + datetime.timedelta(days=7),
            organizer=self.organizer,
            capacity=100
        )

        # Crear código de descuento válido
        self.discount_code = DiscountCode.objects.create(
            code="SAVE25",
            discount_percentage=25.00,
            event=self.event,
            valid_from=timezone.now() - datetime.timedelta(hours=1),
            valid_until=timezone.now() + datetime.timedelta(days=5),
            active=True
        )

    def get_post_data(self, ticket_code, discount_code_id=None):
        return {
            'ticket_code': ticket_code,
            'quantity': '2',
            'type': 'general',
            'discount_code_id': discount_code_id or '',
            'card_number': '4111111111111111',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'Test User'
        }

    def test_successful_ticket_purchase_with_discount_code(self):
        """Compra exitosa con código de descuento válido"""
        self.client.login(username='comprador_test', password='password123')

        post_data = self.get_post_data('TICKET001', str(self.discount_code.id))
        response = self.client.post(
            reverse('ticket_compra', kwargs={'event_id': self.event.id}),
            data=post_data
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('events'))

        ticket = Ticket.objects.get(ticket_code='TICKET001')
        self.assertEqual(ticket.user, self.buyer)
        self.assertEqual(ticket.event, self.event)
        self.assertEqual(ticket.quantity, 2)
        self.assertEqual(ticket.discount_code, self.discount_code)
        self.assertEqual(ticket.discount_percentage, 25)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('¡Compra exitosa!' in str(m) for m in messages))

    def test_ticket_purchase_with_expired_discount_code(self):
        """Compra con código de descuento expirado debería fallar"""
        self.client.login(username='comprador_test', password='password123')

        expired_code = DiscountCode.objects.create(
            code="EXPIRED",
            discount_percentage=30.00,
            event=self.event,
            valid_from=timezone.now() - datetime.timedelta(days=5),
            valid_until=timezone.now() - datetime.timedelta(days=1),
            active=True
        )

        post_data = self.get_post_data('TICKET002', str(expired_code.id))
        response = self.client.post(
            reverse('ticket_compra', kwargs={'event_id': self.event.id}),
            data=post_data
        )

        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("El código de descuento ya no es válido" in str(m) for m in messages),
                        "Debe mostrarse mensaje de código expirado")
        self.assertFalse(Ticket.objects.filter(ticket_code='TICKET002').exists())

