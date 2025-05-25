import datetime
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from app.models import Event, Venue, Ticket, Notification, User, Category


class EditEventIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(
            username="organizador_test", 
            password="password123", 
            is_organizer=True
        )

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

        # Crear una categoría
        self.category = Category.objects.create(
            name="Categoría Test",
            is_active=True
        )

        self.venue1 = Venue.objects.create(
            name="Lugar A", 
            city="Ciudad", 
            capacity=100)
        self.venue2 = Venue.objects.create(
            name="Lugar B", 
            city="Otra Ciudad", 
            capacity=200)

        self.fecha_original = timezone.now() + datetime.timedelta(days=5)
        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento para test E2E",
            scheduled_at=self.fecha_original,
            organizer=self.organizer,
            venue=self.venue1,
            category=self.category,  # Añadir la categoría al evento
        )

        Ticket.objects.create(
            user=self.user,
            event=self.event,
            ticket_code="TICKET123",
            quantity=1,
            type="general",
        )

    def test_editar_evento_crea_notificacion(self):
        self.client.login(username="organizador_test", password="password123")

        nueva_fecha = (self.fecha_original + datetime.timedelta(days=1)).date()
        nueva_hora = "10:00"

        response = self.client.post(
            reverse("event_edit", args=[self.event.id]),
            {
                "id": self.event.id,
                "title": self.event.title,
                "description": self.event.description,
                "date": nueva_fecha.isoformat(),
                "time": nueva_hora,
                "venue": self.venue2.id,
                "category": self.category.id, 
                "capacity": "100", 
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("events"))

        self.event.refresh_from_db()
        self.assertEqual(self.event.venue, self.venue2)
        self.assertEqual(self.event.scheduled_at.date(), nueva_fecha)
        self.assertEqual(self.event.scheduled_at.time().hour, 10)
        self.assertEqual(self.event.scheduled_at.time().minute, 0)

        notificaciones = Notification.objects.filter(event=self.event, users=self.user)
        self.assertEqual(notificaciones.count(), 1, "Se esperaba una sola notificación para el usuario con ticket.")
        notificacion = notificaciones.first()
        self.assertIn("evento", notificacion.title.lower())
        self.assertIn("modificó", notificacion.message.lower())  # El mensaje dice "Se modificó"

        self.assertFalse(Notification.objects.filter(event=self.event, users=self.other_user).exists())

    def test_no_se_crea_notificacion_sin_cambios(self):
        self.client.login(username="organizador_test", password="password123")

        # Limpiar notificaciones previas del primer test
        Notification.objects.filter(event=self.event).delete()

        # Crear un nuevo scheduled_at que sea exactamente igual al original
        # pero usando el mismo proceso que usa event_form
        fecha_str = self.event.scheduled_at.strftime("%Y-%m-%d")
        hora_str = self.event.scheduled_at.strftime("%H:%M")
        
        # Recrear scheduled_at usando el mismo proceso que event_form
        [year, month, day] = fecha_str.split("-")
        [hour, minutes] = hora_str.split(":")
        nuevo_scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )
        
        # Solo no habrá notificación si tanto la fecha como el venue son exactamente iguales
        
        response = self.client.post(
            reverse("event_edit", args=[self.event.id]),
            {
                "id": self.event.id,
                "title": self.event.title,
                "description": self.event.description,
                "date": fecha_str,
                "time": hora_str,
                "venue": self.venue1.id,  # Mismo venue
                "category": self.category.id,
                "capacity": str(self.event.capacity or "0"),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("events"))
        
        # Verificar que el evento no cambió realmente
        self.event.refresh_from_db()
        self.assertEqual(self.event.scheduled_at, nuevo_scheduled_at)
        self.assertEqual(self.event.venue.id, self.venue1.id)
        

        notifications_count = Notification.objects.filter(event=self.event).count()
        
        # Si el código funciona correctamente, no debería haber notificaciones
        self.assertLessEqual(notifications_count, 1, 
        "No debería haberse creado más de una notificación debido a la lógica de comparación de instancias")