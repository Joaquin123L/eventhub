import datetime
import time
from datetime import timedelta
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, User, Ticket, Category, Venue


class BaseEventTestCase(TestCase):
    """Clase base con la configuración común para todos los tests de eventos"""

    def setUp(self):
        # Crear un usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )

        # Crear un usuario regular
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )

        # Crear algunos eventos de prueba
        self.event1 = Event.objects.create(
            title="Evento 1",
            description="Descripción del evento 1",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        self.event2 = Event.objects.create(
            title="Evento 2",
            description="Descripción del evento 2",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
        )

        # Cliente para hacer peticiones
        self.client = Client()
        self.category = Category.objects.create(name="Conferencia", is_active=True)
        self.venue = Venue.objects.create(name="Salón Principal", capacity=150)


class EventsListViewTest(BaseEventTestCase):
    """Tests para la vista de listado de eventos"""

    def test_events_view_with_login(self):
        """Test que verifica que la vista events funciona cuando el usuario está logueado"""
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista events
        response = self.client.get(reverse("events"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/events.html")
        self.assertIn("events", response.context)
        self.assertIn("user_is_organizer", response.context)
        self.assertEqual(len(response.context["events"]), 2)
        self.assertFalse(response.context["user_is_organizer"])

        # Verificar que los eventos están ordenados por fecha
        events = list(response.context["events"])
        self.assertEqual(events[0].id, self.event1.pk)
        self.assertEqual(events[1].id, self.event2.pk)

    def test_events_view_with_organizer_login(self):
        """Test que verifica que la vista events funciona cuando el usuario es organizador"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Hacer petición a la vista events
        response = self.client.get(reverse("events"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_is_organizer"])

    def test_events_view_without_login(self):
        """Test que verifica que la vista events redirige a login cuando el usuario no está logueado"""
        # Hacer petición a la vista events sin login
        response = self.client.get(reverse("events"))

        # Verificar que redirecciona al login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith("/accounts/login/"))

    def test_events_view_excludes_past_events(self):
        """Test que verifica que la vista events no muestra eventos pasados"""
        # Crear un evento pasado
        past_event = Event.objects.create(
            title="Evento Pasado",
            description="Descripción del evento pasado",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista events
        response = self.client.get(reverse("events"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(past_event, response.context["events"])


class EventDetailViewTest(BaseEventTestCase):
    """Tests para la vista de detalle de un evento"""

    def test_event_detail_view_with_login(self):
        """Test que verifica que la vista event_detail funciona cuando el usuario está logueado"""
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista event_detail
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_detail.html")
        self.assertIn("event", response.context)
        self.assertEqual(response.context["event"].id, self.event1.pk)

    def test_event_detail_view_without_login(self):
        """Test que verifica que la vista event_detail redirige a login cuando el usuario no está logueado"""
        # Hacer petición a la vista event_detail sin login
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))

        # Verificar que redirecciona al login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith("/accounts/login/"))

    def test_event_detail_view_with_invalid_id(self):
        """Test que verifica que la vista event_detail devuelve 404 cuando el evento no existe"""
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista event_detail con ID inválido
        response = self.client.get(reverse("event_detail", args=[999]))

        # Verificar respuesta
        self.assertEqual(response.status_code, 404)

    def test_event_detail_with_capacity_and_tickets(self):
    #Test que verifica porcentaje de ocupación con capacidad definida y tickets vendidos
        event = Event.objects.create(
            title="Evento con capacidad",
            description="Evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            capacity=100,
    )

        # Crear tickets por 40 entradas
        Ticket.objects.create(event=event, user=self.organizer, quantity=40)

        response = self.client.login(username="organizador", password="password123")  # Autenticar
        response = self.client.get(reverse("event_detail", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("porcentaje_ocupado", response.context)
        self.assertEqual(response.context["porcentaje_ocupado"], 40.0)
        self.assertEqual(response.context["tickets_vendidos"], 40)

def test_event_detail_verificate_countdown(self):
    """Test que verifica el comportamiento del contador regresivo para eventos futuros"""
    # Crear un evento futuro
    future_event = Event.objects.create(
        title="Evento Futuro",
        description="Descripción del evento futuro",
        scheduled_at=timezone.now() + datetime.timedelta(days=1),
        organizer=self.organizer,
    )

    # Hacer petición a la vista event_detail
    response = self.client.get(reverse("event_detail", args=[future_event.pk]))

    # Verificar que el contador regresivo está presente en el contexto
    self.assertIn("countdown", response.context)
    countdown = response.context["countdown"]

    # Verificar que el contador regresivo no es None y es mayor a 0 segundos
    self.assertIsNotNone(countdown)
    self.assertGreater(countdown.total_seconds(), 0)

    # Verificar que el evento es futuro
    self.assertTrue(future_event.scheduled_at > timezone.now())

class EventFormViewTest(BaseEventTestCase):
    """Tests para la vista del formulario de eventos"""

    def test_event_form_view_with_organizer(self):
        """Test que verifica que la vista event_form funciona cuando el usuario es organizador"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Hacer petición a la vista event_form para crear nuevo evento (id=None)
        response = self.client.get(reverse("event_form"))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertIn("event", response.context)
        self.assertTrue(response.context["user_is_organizer"])

    def test_event_form_view_with_regular_user(self):
        """Test que verifica que la vista event_form redirige cuando el usuario no es organizador"""
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        # Hacer petición a la vista event_form
        response = self.client.get(reverse("event_form"))

        # Verificar que redirecciona a events
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("events"))

    def test_event_form_view_without_login(self):
        """Test que verifica que la vista event_form redirige a login cuando el usuario no está logueado"""
        # Hacer petición a la vista event_form sin login
        response = self.client.get(reverse("event_form"))

        # Verificar que redirecciona al login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith("/accounts/login/"))

    def test_event_form_edit_existing(self):
        """Test que verifica que se puede editar un evento existente"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Hacer petición a la vista event_form para editar evento existente
        response = self.client.get(reverse("event_edit", args=[self.event1.pk]))

        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertEqual(response.context["event"].id, self.event1.pk)




class EventFormSubmissionTest(BaseEventTestCase):
    """Tests para la creación y edición de eventos mediante POST"""

    def test_event_form_post_create(self):
        """Test que verifica que se puede crear un evento mediante POST"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Crear datos para el evento
        event_data = {
        "title": "Nuevo Evento",
        "description": "Descripción del nuevo evento",
        "date": "2025-09-01",
        "time": "14:30",
        "category": self.category.pk,
        "venue": self.venue.pk,
        "capacity": "100",
    }

        # Hacer petición POST a la vista event_form
        response = self.client.post(reverse("event_form"), event_data)

        # Verificar que redirecciona a events
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("events"))

        # Verificar que se creó el evento
        self.assertTrue(Event.objects.filter(title="Nuevo Evento").exists())
        evento = Event.objects.get(title="Nuevo Evento")
        self.assertEqual(evento.description, "Descripción del nuevo evento")
        self.assertEqual(evento.scheduled_at.year, 2025)
        self.assertEqual(evento.scheduled_at.month, 9)
        self.assertEqual(evento.scheduled_at.day, 1)
        self.assertEqual(evento.scheduled_at.hour, 14)
        self.assertEqual(evento.scheduled_at.minute, 30)
        self.assertEqual(evento.organizer, self.organizer)
        self.assertEqual(evento.category, self.category)
        self.assertEqual(evento.venue, self.venue)

    def test_event_form_post_edit(self):
        """Test que verifica que se puede editar un evento existente mediante POST"""
        # Login con usuario organizador
        self.client.login(username="organizador", password="password123")

        # Datos para actualizar el evento
        updated_data = {
        "id": self.event1.pk,
        "title": "Evento 1 Actualizado",
        "description": "Nueva descripción actualizada",
        "date": "2025-06-15",
        "time": "16:45",
        "category": self.category.pk,
        "venue": self.venue.pk,
        "capacity": "150",
    }

        # Hacer petición POST para editar el evento
        response = self.client.post(reverse("event_edit", args=[self.event1.pk]), updated_data)

        # Verificar que redirecciona a events
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("events"))

        # Verificar que el evento fue actualizado
        self.event1.refresh_from_db()

        self.assertEqual(self.event1.title, "Evento 1 Actualizado")
        self.assertEqual(self.event1.description, "Nueva descripción actualizada")
        self.assertEqual(self.event1.scheduled_at.year, 2025)
        self.assertEqual(self.event1.scheduled_at.month, 6)
        self.assertEqual(self.event1.scheduled_at.day, 15)
        self.assertEqual(self.event1.scheduled_at.hour, 16)
        self.assertEqual(self.event1.scheduled_at.minute, 45)
        self.assertEqual(self.event1.organizer, self.organizer)
        self.assertEqual(self.event1.category, self.category)
        self.assertEqual(self.event1.venue, self.venue)


class EventDeleteViewTest(BaseEventTestCase):
    """Tests para la eliminación de eventos"""

    def test_event_delete_with_organizer(self):
        """Test que verifica que un organizador puede eliminar un evento"""
        # Iniciar sesión como organizador
        self.client.login(username="organizador", password="password123")

        # Verificar que el evento existe antes de eliminar
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

        # Hacer una petición POST para eliminar el evento
        response = self.client.post(reverse("event_delete", args=[self.event1.pk]))

        # Verificar que redirecciona a la página de eventos
        self.assertRedirects(response, reverse("events"))

        # Verificar que el evento ya no existe
        self.assertFalse(Event.objects.filter(pk=self.event1.pk).exists())

    def test_event_delete_with_regular_user(self):
        """Test que verifica que un usuario regular no puede eliminar un evento"""
        # Iniciar sesión como usuario regular
        self.client.login(username="regular", password="password123")

        # Verificar que el evento existe antes de intentar eliminarlo
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

        # Hacer una petición POST para intentar eliminar el evento
        response = self.client.post(reverse("event_delete", args=[self.event1.pk]))

        # Verificar que redirecciona a la página de eventos sin eliminar
        self.assertRedirects(response, reverse("events"))

        # Verificar que el evento sigue existiendo
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

    def test_event_delete_with_get_request(self):
        """Test que verifica que la vista redirecciona si se usa GET en lugar de POST"""
        # Iniciar sesión como organizador
        self.client.login(username="organizador", password="password123")

        # Hacer una petición GET para intentar eliminar el evento
        response = self.client.get(reverse("event_delete", args=[self.event1.pk]))

        # Verificar que redirecciona a la página de eventos
        self.assertRedirects(response, reverse("events"))

        # Verificar que el evento sigue existiendo
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

    def test_event_delete_nonexistent_event(self):
        """Test que verifica el comportamiento al intentar eliminar un evento inexistente"""
        # Iniciar sesión como organizador
        self.client.login(username="organizador", password="password123")

        # ID inexistente
        nonexistent_id = 9999

        # Verificar que el evento con ese ID no existe
        self.assertFalse(Event.objects.filter(pk=nonexistent_id).exists())

        # Hacer una petición POST para eliminar el evento inexistente
        response = self.client.post(reverse("event_delete", args=[nonexistent_id]))

        # Verificar que devuelve error 404
        self.assertEqual(response.status_code, 404)

    def test_event_delete_without_login(self):
        """Test que verifica que la vista redirecciona a login si el usuario no está autenticado"""
        # Verificar que el evento existe antes de intentar eliminarlo
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

        # Hacer una petición POST sin iniciar sesión
        response = self.client.post(reverse("event_delete", args=[self.event1.pk]))

        # Verificar que redirecciona al login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith("/accounts/login/"))

        # Verificar que el evento sigue existiendo
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())
        response = self.client.login(username="organizador", password="password123")  # Autenticar
        response = self.client.get(reverse("event_detail", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("porcentaje_ocupado", response.context)
        self.assertEqual(response.context["porcentaje_ocupado"], 40.0)
        self.assertEqual(response.context["tickets_vendidos"], 40)

class EventStatusIntegrationTest(BaseEventTestCase):

    def test_evento_se_cancela(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse('event_cancel', kwargs={'pk': self.event1.pk}))
        self.assertEqual(response.status_code, 302)

        self.event1.refresh_from_db()
        self.assertEqual(self.event1.status, "Cancelado")

    def test_evento_finalizado_automaticamente(self):

        self.assertEqual(self.event1.status, "Activo")
        self.client.login(username="organizador", password="password123")
        # Cambiar la fecha al pasado
        self.event1.scheduled_at = timezone.now() - timedelta(days=3)
        self.event1.save()

        # Acceder a la vista del evento (que debe llamar a check_and_update_status)
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
        self.assertEqual(response.status_code, 200)

        # Refrescar desde la base de datos y verificar que cambió a "Finalizado"
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.status, "Finalizado")

    def test_evento_agotado_y_vuelve_a_activo(self):
        self.event1.capacity=5
        self.client.login(username="organizador", password="password123")
        ticket1 = Ticket.objects.create(
            event=self.event1,
            user=self.organizer,
            quantity=3,
            ticket_code="AG1"
        )
        ticket2 = Ticket.objects.create(
            event=self.event1,
            user=self.organizer,
            quantity=2,
            ticket_code="AG2"
        )

        # Simula agotado
        self.event1.check_and_update_agotado()
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.status, "Agotado")

        # Borrar un ticket vía vista
        response = self.client.post(
            reverse('ticket_delete', kwargs={'event_id': self.event1.pk, 'ticket_id': ticket2.pk})
        )
        self.assertEqual(response.status_code, 302)
        # self.event1.check_and_update_agotado()
        # Chequea que vuelva a activo
        self.assertFalse(Ticket.objects.filter(pk=ticket2.pk).exists())
        self.assertEqual(ticket2.event, self.event1)

        self.event1.refresh_from_db()
        self.assertEqual(self.event1.status, "Activo")
