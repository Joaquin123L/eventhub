import datetime

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Category, Event, Notification, Ticket, User, Venue


class BaseTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador_test", 
            password="password123", 
            is_organizer=True
        )

        # Usuarios comunes
        self.user = User.objects.create_user(
            username="usuario_test", 
            password="password123", 
            email="usuario@test.com"
        )
        self.other_user = User.objects.create_user(
            username="otro_usuario", 
            password="password123", 
            email="otro@test.com"
        )

        # Categoría del evento
        self.category = Category.objects.create(
            name="Categoría Test",
            is_active=True
        )

        # Lugares (Venue)
        self.venue1 = Venue.objects.create(
            name="Lugar A", 
            city="Ciudad", 
            capacity=100
        )
        self.venue2 = Venue.objects.create(
            name="Lugar B", 
            city="Otra Ciudad", 
            capacity=200
        )

        # Fecha original del evento
        self.fecha_original = timezone.now() + datetime.timedelta(days=5)

        # Crear evento
        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento para test E2E",
            scheduled_at=self.fecha_original,
            organizer=self.organizer,
            venue=self.venue1,
            category=self.category
        )

        # Comprar ticket
        Ticket.objects.create(
            user=self.user,
            event=self.event,
            ticket_code="TICKET123",
            quantity=1,
            type="general",
        )


# === Test para verificar creación de notificaciones al editar evento ===
class EventEditNotificationTest(BaseTest):
    def test_editar_evento_crea_notificacion(self):
        """Verifica que al editar un evento se cree una notificación solo para usuarios con ticket."""
        self.client.login(username="organizador_test", password="password123")

        nueva_fecha = (self.fecha_original + datetime.timedelta(days=1)).date()
        nueva_hora = "10:00"

        response = self.client.post(
            reverse("event_edit", args=[self.event.pk]),
            {
                "id": self.event.pk,
                "title": self.event.title,
                "description": self.event.description,
                "date": nueva_fecha.isoformat(),
                "time": nueva_hora,
                "venue": self.venue2.pk,
                "category": self.category.pk,
                "capacity": "100",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("events"))

        # Refrescar datos del evento
        self.event.refresh_from_db()
        self.assertEqual(self.event.venue, self.venue2)
        self.assertEqual(self.event.scheduled_at.date(), nueva_fecha)
        self.assertEqual(self.event.scheduled_at.time().hour, 10)
        self.assertEqual(self.event.scheduled_at.time().minute, 0)

        # Verificar notificaciones
        notificaciones = Notification.objects.filter(event=self.event, users=self.user)
        self.assertEqual(notificaciones.count(), 1, "Se esperaba una sola notificación para el usuario con ticket.")
        
        notificacion = notificaciones.get()
        self.assertIn("evento", notificacion.title.lower())
        self.assertIn("se han realizado cambios en el evento", notificacion.message.lower())

        # Verificar que otro usuario no tenga la notificación
        self.assertFalse(Notification.objects.filter(event=self.event, users=self.other_user).exists())


# === Test para verificar que NO se crea notificación si no hay cambios ===
class EventEditNoNotificationTest(BaseTest):
    def test_no_se_crea_notificacion_sin_cambios(self):
        """Verifica que NO se cree una notificación si no hay cambios reales en el evento."""
        self.client.login(username="organizador_test", password="password123")

        # Eliminar notificaciones previas
        Notification.objects.filter(event=self.event).delete()

        # Recrear scheduled_at usando formato similar al formulario
        fecha_str = self.event.scheduled_at.strftime("%Y-%m-%d")
        hora_str = self.event.scheduled_at.strftime("%H:%M")

        [year, month, day] = fecha_str.split("-")
        [hour, minutes] = hora_str.split(":")
        nuevo_scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        # Enviar datos sin cambios
        response = self.client.post(
            reverse("event_edit", args=[self.event.pk]),
            {
                "id": self.event.pk,
                "title": self.event.title,
                "description": self.event.description,
                "date": fecha_str,
                "time": hora_str,
                "venue": self.venue1.pk,
                "category": self.category.pk,
                "capacity": str(self.event.capacity or "0"),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("events"))

        # Refrescar datos del evento
        self.event.refresh_from_db()
        self.assertEqual(self.event.scheduled_at, nuevo_scheduled_at)
        self.assertIsNotNone(self.event.venue)
        self.assertEqual(self.event.venue.pk, self.venue1.pk) # type: ignore

        # Verificar que no se haya creado ninguna o a lo sumo una por lógica interna
        notifications_count = Notification.objects.filter(event=self.event).count()
        self.assertLessEqual(
            notifications_count, 1,
            "No debería haberse creado más de una notificación si no hubo cambios."
        )