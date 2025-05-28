import re
from datetime import datetime, timedelta

from django.utils import timezone
from playwright.sync_api import expect

from app.models import User, Event, Category, Venue, Ticket, Notification, NotificationUser
from app.test.test_e2e.base import BaseE2ETest


class BaseEventNotificationTest(BaseE2ETest):
    """
    Configuración-> usuarios, evento, venue, categoría y ticket inicial.
    """

    def setUp(self):
        super().setUp()
        # Crear datos de prueba
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com", 
            password="password123",
            is_organizer=True
        )
        
        self.user_with_ticket = User.objects.create_user(
            username="usuario_con_ticket",
            email="usuario@example.com",
            password="password123",
            is_organizer=False
        )
        
        self.user_without_ticket = User.objects.create_user(
            username="usuario_sin_ticket", 
            email="sin_ticket@example.com",
            password="password123",
            is_organizer=False
        )
        
        # Crear categoría
        self.category = Category.objects.create(
            name="Categoría Test",
            description="Categoría para testing"
        )
        
        # Crear venues
        self.original_venue = Venue.objects.create(
            name="Venue Original",
            address="Dirección Original 123",
            city="Ciudad Original",
            capacity=100
        )
        
        self.new_venue = Venue.objects.create(
            name="Venue Nuevo", 
            address="Dirección Nueva 456",
            city="Ciudad Nueva",
            capacity=150
        )
        
        # Crear evento
        original_date = timezone.now() + timedelta(days=30)
        self.event = Event.objects.create(
            title="Evento Test",
            description="Descripción del evento de prueba",
            scheduled_at=original_date,
            organizer=self.organizer,
            category=self.category,
            venue=self.original_venue,
            capacity=50
        )
        
        # Crear ticket para un usuario
        self.ticket = Ticket.objects.create(
            ticket_code="TICKET001",
            quantity=1,
            user=self.user_with_ticket,
            event=self.event,
            type='general'
        )


class TestEventDateChangeNotification(BaseEventNotificationTest):
    """
    Pruebas relacionadas con notificaciones automáticas al cambiar la fecha del evento.
    - Se crea notificación con mensaje detallado sobre el cambio de fecha.
    - Solo los usuarios con tickets reciben la notificación.
    """

    def test_notification_on_date_change(self):
        """Verifica que se envía notificación automática al cambiar la fecha del evento"""
        
        old_scheduled_at = self.event.scheduled_at
        new_scheduled_at = old_scheduled_at + timedelta(days=5)

        # Login como organizador
        self.login_user(self.organizer.username, "password123")
        
        # Ir al formulario de edición del evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/edit/")

        # Verificar que estamos en la página correcta
        header = self.page.locator("h1")
        expect(header).to_have_text("Editar evento")
        expect(header).to_be_visible()
        
        self.page.fill("input[name='date']", new_scheduled_at.date().strftime("%Y-%m-%d"))
        current_time = old_scheduled_at.time()
        self.page.fill("input[name='time']", current_time.strftime("%H:%M"))

        # Enviar el formulario
        self.page.locator("button:has-text('Guardar Cambios')").click()

        # Después de hacer click en submit
        expect(self.page.locator(".error-message")).not_to_be_visible(timeout=5000)

        # Verificar que se redirige a la lista de eventos
        self.page.wait_for_url(f"{self.live_server_url}/events/")
        #Esto devuelve un queryset
        notifications = Notification.objects.filter(title="Cambio en evento", event=self.event)
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.get()
        self.assertEqual(notification.priority, "HIGH")
        self.assertIn("Se han realizado cambios en el evento", notification.message)   
        # Verificar que solo el usuario con ticket (asociado al evento) recibió la notificación
        notification_users = NotificationUser.objects.filter(notification=notification)
        self.assertEqual(notification_users.count(), 1)
        notification_user = notification_users.get()
        self.assertEqual(notification_user.user, self.user_with_ticket)

        # Verificar que el usuario sin ticket NO recibió la notificación
        user_without_ticket_notifications = NotificationUser.objects.filter(
            user=self.user_without_ticket,
            notification=notification
        )
        self.assertEqual(user_without_ticket_notifications.count(), 0)


class TestEventVenueChangeNotification(BaseEventNotificationTest):
    """
    Pruebas relacionadas con notificaciones automáticas al cambiar el lugar del evento.
    - Se crea notificación con mensaje detallado sobre el cambio de lugar.
    - Solo los usuarios con tickets reciben la notificación.
    """

    def test_notification_on_venue_change(self):
        """Verifica que se envía notificación automática al cambiar el lugar del evento"""
        
        old_venue = self.event.venue
        new_venue = self.new_venue

        self.login_user(self.organizer.username, "password123")
        
        # Ir al formulario de edición del evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/edit/")
        
        # Cambiar el venue del evento
        self.page.select_option("select[name='venue']", str(self.new_venue.pk))
        
        # Enviar el formulario
        self.page.locator("button:has-text('Guardar Cambios')").click()
        
        # Verificar redirección
        self.page.wait_for_url(f"{self.live_server_url}/events/*")

        notifications = Notification.objects.filter(title="Cambio en evento", event=self.event)
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.get()
        self.assertIsNotNone(notification)
        self.assertIn("Se han realizado cambios en el evento", notification.message)

        expected_venue_text = f"Lugar: de {old_venue.name if old_venue else 'sin lugar'} a {new_venue.name}"
        self.assertIn(expected_venue_text, notification.message)

        notification_users = NotificationUser.objects.filter(notification=notification, user=self.user_with_ticket)
        self.assertEqual(notification_users.count(), 1)


class TestEventNotificationUIVisibility(BaseEventNotificationTest):
    """
    Pruebas relacionadas con la visibilidad de notificaciones en la interfaz de usuario.
    - El usuario con ticket debe ver el mensaje correcto tras un cambio en el evento.
    """

    def test_user_can_see_notification_in_ui(self):
        """Verifica que el usuario con ticket puede ver la notificación en la interfaz"""
        
        self.context.clear_cookies()
        
        # Como organizador
        self.login_user(self.organizer.username, "password123")
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/edit/")

        old_scheduled_at = self.event.scheduled_at
        new_scheduled_at = old_scheduled_at + timedelta(days=5)

        self.page.fill("input[name='date']", new_scheduled_at.strftime("%Y-%m-%d"))
        self.page.locator("button:has-text('Guardar Cambios')").click()
        
        # Nueva sesión
        self.context.close()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Login como usuario con ticket
        self.login_user(self.user_with_ticket.username, "password123")
        
        # ir a la vista de notificaciones
        self.page.goto(f"{self.live_server_url}/notifications/visualizacion")

        expect(self.page.locator("body")).to_contain_text("Se han realizado cambios en el evento")

        expected_date_text = f"Fecha/Hora: de {old_scheduled_at.strftime('%d/%m/%Y %H:%M')} a {new_scheduled_at.strftime('%d/%m/%Y %H:%M')}"
        expect(self.page.locator("body")).to_contain_text(expected_date_text)