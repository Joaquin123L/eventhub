from django.test import TestCase
from app.models import User, Notification, Event, Venue, Ticket
from django.utils import timezone
from datetime import timedelta


class BaseTestSetup(TestCase):
    """
    Configuración base para pruebas que comparten usuarios, evento, lugar y ticket.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(username="usuario1", password="pass123")
        self.user2 = User.objects.create_user(username="usuario2", password="pass123")

        self.venue1 = Venue.objects.create(name="Lugar Original", address="Calle 123")
        self.venue2 = Venue.objects.create(name="Nueva Ubicación", address="Calle 456")

        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento de prueba",
            scheduled_at=timezone.now() + timedelta(days=5),
            organizer=self.user1,
            venue=self.venue1,
            capacity=100
        )

        Ticket.objects.create(
            event=self.event,
            user=self.user1,
            quantity=1,
            ticket_code="TICKET1"
        )
        
        Ticket.objects.create(
            event=self.event,
            user=self.user2,
            quantity=2,
            ticket_code="TICKET2"
        )

class TestEventUpdateTriggersNotification(BaseTestSetup):
    """
    Pruebas relacionadas con la creacion notificaciones por cambio de fecha y/o lugar del evento.
    """

    def test_create_notification_for_event_date_change(self):
        # Crea notificación por cambio de fecha del evento
        nueva_fecha = self.event.scheduled_at + timedelta(days=1)

        success, errors = self.event.update(
            title=self.event.title,
            description=self.event.description,
            scheduled_at=nueva_fecha,
            organizer=self.event.organizer
        )
        
        self.assertTrue(success)
        self.assertIsNone(errors)
        
        # Verificar que la notificación fue creada correctamente


        notif = Notification.objects.get(event=self.event)
        self.assertIn("Fecha/Hora", notif.message)
        self.assertEqual(notif.users.count(), 2)

    def test_create_notification_for_event_location_change(self):
        # Crea notificación especifica por cambio de ubicación del evento

        success, errors = self.event.update(
            title=self.event.title,
            description=self.event.description,
            scheduled_at=self.event.scheduled_at,
            organizer=self.event.organizer,
            venue=self.venue2
        )

        self.assertTrue(success)
        self.assertIsNone(errors)

        notif = Notification.objects.get(event=self.event)
        # Verificar que la notificación fue creada correctamente
        self.assertIn("Lugar", notif.message)
        self.assertIn("Nueva Ubicación", notif.message)
        self.assertEqual(notif.users.count(), 2)

    def test_notification_created_on_both_date_and_location_change(self):
        # Crea notificación especifica por cambio de fecha y lugar del evento
        nueva_fecha = self.event.scheduled_at + timedelta(days=3)

        success, errors = self.event.update(
            title=self.event.title,
            description=self.event.description,
            scheduled_at=nueva_fecha,
            organizer=self.event.organizer,
            venue=self.venue2
        )

        self.assertTrue(success)
        self.assertIsNone(errors)

        notif = Notification.objects.get(event=self.event)
        self.assertIn("Fecha/Hora", notif.message)
        self.assertIn("Lugar", notif.message)
        self.assertEqual(notif.users.count(), 2)
