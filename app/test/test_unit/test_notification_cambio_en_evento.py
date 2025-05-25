from django.test import TestCase
from app.models import User, Notification, Event
from django.utils import timezone
from datetime import datetime


class NotificationModelUnitTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="usuario1", password="pass123")
        self.user2 = User.objects.create_user(username="usuario2", password="pass123")

        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento de prueba",
            scheduled_at = timezone.make_aware(datetime(2025, 6, 1, 10, 0, 0)),

            organizer=self.user1,
        )

    def test_create_notification_for_event_date_change(self):
        """Test que verifica la creación de notificación al cambiar fecha del evento"""
        # Crear notificación para cambio de fecha
        success, errors = Notification.new(
            title="Cambio de fecha del evento",
            message=f"La fecha del evento '{self.event.title}' ha sido modificada",
            priority="HIGH",
            users=[self.user1, self.user2],
            event=self.event
        )
        
        self.assertTrue(success)
        self.assertIsNone(errors)
        
        # Verificar que la notificación fue creada correctamente
        notification = Notification.objects.get(title="Cambio de fecha del evento")
        self.assertEqual(notification.priority, "HIGH")
        self.assertEqual(notification.event, self.event)
        self.assertEqual(notification.users.count(), 2)
        self.assertIn(self.user1, notification.users.all())
        self.assertIn(self.user2, notification.users.all())

    def test_create_notification_for_event_location_change(self):
        """Test que verifica la creación de notificación al cambiar ubicación del evento"""
        new_location = "Nueva Ubicación"
        
        # Crear notificación para cambio de ubicación
        success, errors = Notification.new(
            title="Cambio de ubicación del evento",
            message=f"La ubicación del evento '{self.event.title}' ha sido cambiada a: {new_location}",
            priority="HIGH", 
            users=[self.user1, self.user2],
            event=self.event
        )
        
        self.assertTrue(success)
        self.assertIsNone(errors)
        
        # Verificar que la notificación fue creada correctamente
        notification = Notification.objects.get(title="Cambio de ubicación del evento")
        self.assertEqual(notification.priority, "HIGH")
        self.assertEqual(notification.event, self.event)
        self.assertIn("Nueva Ubicación", notification.message)
        self.assertEqual(notification.users.count(), 2)


    def test_crear_notificacion_para_multiples_usuarios(self):
        """Test unitario: Notification.new() asigna usuarios correctamente"""

        success, errors = Notification.new(
            title="Prueba",
            message="Mensaje de prueba",
            priority="HIGH",
            users=[self.user1, self.user2],
            event=self.event
        )

        self.assertTrue(success)
        self.assertIsNone(errors)

        notificacion = Notification.objects.last()
        self.assertIsNotNone(notificacion)  # Asegura que no es None
        self.assertEqual(notificacion.title, "Prueba")
        self.assertEqual(notificacion.message, "Mensaje de prueba")
        self.assertEqual(notificacion.priority, "HIGH")
        self.assertEqual(notificacion.event, self.event)
        self.assertEqual(notificacion.users.count(), 2)
        self.assertIn(self.user1, notificacion.users.all())
        self.assertIn(self.user2, notificacion.users.all())

 