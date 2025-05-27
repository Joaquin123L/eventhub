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
            discount_percentage=20  # Se conserva el porcentaje
        )
        
        # Verificar que el ticket se creó correctamente con el descuento
        self.assertEqual(ticket.discount_code, discount_code)
        self.assertEqual(ticket.discount_percentage, 20)
        self.assertEqual(ticket.discount_code.code, "SAVE20")
        self.assertTrue(ticket.discount_code.is_valid())
        
        # Verificar que el descuento pertenece al mismo evento que el ticket
        self.assertEqual(ticket.discount_code.event, ticket.event)



    def test_ticket_creation_preserves_discount_when_code_deleted(self):
        """Test que verifica que el porcentaje se conserva aunque se elimine el código"""
        # Crear código de descuento válido
        valid_from = timezone.now() - datetime.timedelta(hours=1)
        valid_until = timezone.now() + datetime.timedelta(days=5)
        
        discount_code = DiscountCode.objects.create(
            code="TEMP30",
            discount_percentage=30.00,
            event=self.event,
            valid_from=valid_from,
            valid_until=valid_until,
            active=True
        )
        
        # Crear usuario para el ticket
        user = User.objects.create_user(
            username="buyer_test2",
            email="buyer2@example.com",
            password="password123"
        )
        
        # Crear ticket con código de descuento
        from app.models import Ticket
        ticket = Ticket.objects.create(
            ticket_code="TICKET002",
            quantity=1,
            user=user,
            event=self.event,
            discount_code=discount_code,
            discount_percentage=30
        )
        
        # Verificar que el ticket tiene el descuento aplicado
        self.assertEqual(ticket.discount_percentage, 30)
        self.assertIsNotNone(ticket.discount_code)
        
        # Eliminar el código de descuento (SET_NULL)
        discount_code.delete()
        
        # Recargar el ticket desde la base de datos
        ticket.refresh_from_db()
        
        # Verificar que el porcentaje se conservó aunque el código se eliminó
        self.assertIsNone(ticket.discount_code)  # El código se eliminó
        self.assertEqual(ticket.discount_percentage, 30)  # El porcentaje se conserva
