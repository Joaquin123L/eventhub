import datetime
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from app.models import Event, Ticket, User


class EventModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        self.future_date = timezone.now() + timedelta(days=5)
        self.past_date = timezone.now() - timedelta(days=5)

    def test_event_creation(self):
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )
        """Test que verifica la creación correcta de eventos"""
        self.assertEqual(event.title, "Evento de prueba")
        self.assertEqual(event.description, "Descripción del evento de prueba")
        self.assertEqual(event.organizer, self.organizer)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_validate_with_valid_data(self):
        """Test que verifica la validación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("Título válido", "Descripción válida", scheduled_at)
        self.assertEqual(errors, {})

    def test_event_validate_with_empty_title(self):
        """Test que verifica la validación de eventos con título vacío"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("", "Descripción válida", scheduled_at)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un titulo")

    def test_event_validate_with_empty_description(self):
        """Test que verifica la validación de eventos con descripción vacía"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("Título válido", "", scheduled_at)
        self.assertIn("description", errors)
        self.assertEqual(errors["description"], "Por favor ingrese una descripcion")

    def test_event_new_with_valid_data(self):
        """Test que verifica la creación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        success, errors = Event.new(
            title="Nuevo evento",
            description="Descripción del nuevo evento",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
        )

        self.assertTrue(success)
        self.assertIsNone(errors)

        # Verificar que el evento fue creado en la base de datos
        new_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(new_event.description, "Descripción del nuevo evento")
        self.assertEqual(new_event.organizer, self.organizer)

    def test_event_new_with_invalid_data(self):
        """Test que verifica que no se crean eventos con datos inválidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        initial_count = Event.objects.count()

        # Intentar crear evento con título vacío
        success, errors = Event.new(
            title="",
            description="Descripción del evento",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
        )

        self.assertFalse(success)
        self.assertIn("title", errors) # type: ignore

        # Verificar que no se creó ningún evento nuevo
        self.assertEqual(Event.objects.count(), initial_count)

    def test_event_update(self):
        """Test que verifica la actualización de eventos"""
        new_title = "Título actualizado"
        new_description = "Descripción actualizada"
        new_scheduled_at = timezone.now() + datetime.timedelta(days=3)

        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        event.update(
            title=new_title,
            description=new_description,
            scheduled_at=new_scheduled_at,
            organizer=self.organizer,
        )

        # Recargar el evento desde la base de datos
        updated_event = Event.objects.get(pk=event.pk)

        self.assertEqual(updated_event.title, new_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at.time(), new_scheduled_at.time())

    def test_event_update_partial(self):
        """Test que verifica la actualización parcial de eventos"""
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        original_title = event.title
        original_scheduled_at = event.scheduled_at
        new_description = "Solo la descripción ha cambiado"

        event.update(
            title=None,  # No cambiar
            description=new_description,
            scheduled_at=None,  # No cambiar
            organizer=None,  # No cambiar
        )

        # Recargar el evento desde la base de datos
        updated_event = Event.objects.get(pk=event.pk)

        # Verificar que solo cambió la descripción
        self.assertEqual(updated_event.title, original_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at, original_scheduled_at)


    def test_event_creation_fails_with_negative_capacity(self):
        scheduled_at = timezone.now() + datetime.timedelta(days=1)

        is_valid, errors = Event.new(
            title="Evento inválido",
            description="Capacidad negativa",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
            capacity=-10  #
        )
        self.assertFalse(is_valid)
        self.assertIn("capacity", errors) # type: ignore

        # El test pasa si al buscar el evento salta DoesNotExist:
        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(title="Evento inválido")


    def test_event_activo_default(self):
        event = Event.objects.create(title="Test Event", capacity=10, scheduled_at=self.future_date, organizer=self.organizer)
        self.assertEqual(event.status, "Activo")

    def test_evento_finalizado_si_fecha_pasada(self):
        event = Event.objects.create(
            title="Evento Pasado",
            capacity=10,
            scheduled_at=self.past_date,
            organizer=self.organizer
        )
        event.check_and_update_status()
        self.assertEqual(event.status, "Finalizado")

    def test_evento_cancelado_no_cambia_estado(self):
        event = Event.objects.create(
            title="Evento Cancelable",
            capacity=10,
            scheduled_at=self.future_date,
            organizer=self.organizer
        )


        event.status = "Cancelado"
        event.save()


        event.check_and_update_status()


        self.assertEqual(event.status, "Cancelado")
    def test_evento_agotado_si_llega_a_capacidad(self):
        event = Event.objects.create(
            title="Evento con Tickets",
            capacity=5,
            scheduled_at=self.future_date,
            organizer=self.organizer
        )

        Ticket.objects.create(
            event=event,
            quantity=3,
            ticket_code="A1",
            user=self.organizer
        )
        Ticket.objects.create(
            event=event,
            quantity=2,
            ticket_code="A2",
            user=self.organizer
        )

        event.check_and_update_agotado()
        self.assertEqual(event.status, "Agotado")

    def test_evento_vuelve_a_activo_si_se_elimina_ticket_y_hay_capacidad(self):
        event = Event.objects.create(
            title="Evento dinámico",
            capacity=5,
            scheduled_at=self.future_date,
            organizer=self.organizer
        )

        ticket1 = Ticket.objects.create(
            event=event,
            quantity=3,
            ticket_code="B1",
            user=self.organizer
        )
        Ticket.objects.create(
            event=event,
            quantity=2,
            ticket_code="B2",
            user=self.organizer
        )

        event.check_and_update_agotado()
        self.assertEqual(event.status, "Agotado")

        ticket1.delete()
        
        event.check_and_update_agotado()

        self.assertEqual(event.status, "Activo")


    def test_event_validation_countdown(self):
        """Test que verifica que si tengo un evento viejo el metodo countdown devuelve None"""
        event = Event.objects.create(
            title="Evento viejo",
            description="Descripción del evento viejo",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )
        self.assertIsNone(event.countdown)

        """Test que verifica que si tengo un evento futuro el metodo countdown devuelve un timedelta"""
        event.scheduled_at = timezone.now() + datetime.timedelta(days=1)
        event.save()
        self.assertIsInstance(event.countdown, datetime.timedelta)

    def test_event_es_pasado_con_fecha_pasada(self):
        """Test que verifica que si tengo un evento pasado el metodo es_pasado devuelve True"""
        event = Event.objects.create(
            title="Evento pasado",
            description="Descripción del evento pasado",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )
        self.assertTrue(event.es_pasado)
