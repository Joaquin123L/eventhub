import datetime

from django.test import TestCase
from django.utils import timezone

from app.models import Event, User, DiscountCode,Ticket


class DiscountCodeModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=7),
            organizer=self.organizer,
        )

    def test_discount_code_creation(self):
        """Test que verifica la creación correcta de códigos de descuento"""
        valid_from = timezone.now()
        valid_until = timezone.now() + datetime.timedelta(days=5)
        
        discount_code = DiscountCode.objects.create(
            code="TEST20",
            discount_percentage=20.00,
            event=self.event,
            valid_from=valid_from,
            valid_until=valid_until,
            active=True
        )
        
        self.assertEqual(discount_code.code, "TEST20")
        self.assertEqual(discount_code.discount_percentage, 20.00)
        self.assertEqual(discount_code.event, self.event)
        self.assertEqual(discount_code.valid_from, valid_from)
        self.assertEqual(discount_code.valid_until, valid_until)
        self.assertTrue(discount_code.active)

    def test_ticket_creation_with_valid_discount_code(self):
        """Test que verifica la creación de tickets con código de descuento válido"""
        # Crear código de descuento válido
        valid_from = timezone.now() - datetime.timedelta(hours=1)
        valid_until = timezone.now() + datetime.timedelta(days=5)
        
        discount_code = DiscountCode.objects.create(
            code="SAVE20",
            discount_percentage=20.00,
            event=self.event,
            valid_from=valid_from,
            valid_until=valid_until,
            active=True
        )
        
        # Crear usuario para el ticket
        user = User.objects.create_user(
            username="comprador",
            email="comprador@example.com",
            password="password123"
        )
        
        # Crear ticket con código de descuento
        ticket = Ticket.objects.create(
            ticket_code="TICKET001",
            quantity=2,
            user=user,
            event=self.event,
            discount_code=discount_code,
        )

        # Verificar que el ticket se creó correctamente con el descuento

        if ticket.discount_code is not None:
            self.assertEqual(ticket.discount_code.code, "SAVE20")
            self.assertTrue(ticket.discount_code.is_valid())
            self.assertEqual(ticket.discount_code.event, ticket.event)
        else:
            self.fail("El campo discount_code es None")
