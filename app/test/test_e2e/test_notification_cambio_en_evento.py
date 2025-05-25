import re
from datetime import datetime, timedelta

from django.utils import timezone
from playwright.sync_api import expect

from app.models import User, Event, Category, Venue, Ticket, Notification, NotificationUser
from app.test.test_e2e.base import BaseE2ETest


class EventNotificationE2ETest(BaseE2ETest):
    """Pruebas E2E para notificaciones automáticas al cambiar eventos"""

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
    print("paso la creacion")

    def test_notification_on_date_change(self):
        """Verifica que se envía notificación automática al cambiar la fecha del evento"""
        
        # Login como organizador
        self.login_user(self.organizer.username, "password123")
        
        # Ir al formulario de edición del evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/edit/")

        # Verificar que estamos en la página correcta
        header = self.page.locator("h1")
        expect(header).to_have_text("Editar evento")
        expect(header).to_be_visible()
        
        # Cambiar la fecha del evento (agregar 5 días)
        new_date = (self.event.scheduled_at + timedelta(days=5)).date()
        self.page.fill("input[name='date']", new_date.strftime("%Y-%m-%d"))
       
        # Mantener la misma hora
        current_time = self.event.scheduled_at.time()
        self.page.fill("input[name='time']", current_time.strftime("%H:%M"))

        # Enviar el formulario
        self.page.locator("button:has-text('Guardar Cambios')").click()

        # Después de hacer click en submit
        expect(self.page.locator(".error-message")).not_to_be_visible(timeout=5000)

        # Verificar que se redirige a la lista de eventos
        self.page.wait_for_url(f"{self.live_server_url}/events/")
        
       
        # Verificar que se creó la notificación en la base de datos
        notifications = Notification.objects.filter(
            title="Cambio en evento",
            event=self.event
        )
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.first()
        self.assertEqual(notification.priority, "HIGH")
        self.assertIn("Se modificó la fecha/hora o el lugar del evento", notification.message) 
   
        # Verificar que solo el usuario con ticket (asociado al evento) recibió la notificación
        notification_users = NotificationUser.objects.filter(notification=notification)
        self.assertEqual(notification_users.count(), 1)
        self.assertEqual(notification_users.first().user, self.user_with_ticket)

        # Verificar que el usuario sin ticket NO recibió la notificación
        user_without_ticket_notifications = NotificationUser.objects.filter(
            user=self.user_without_ticket,
            notification=notification
        )
        self.assertEqual(user_without_ticket_notifications.count(), 0)

    def test_notification_on_venue_change(self):
        """Verifica que se envía notificación automática al cambiar el lugar del evento"""
        
        # Login como organizador
        self.login_user(self.organizer.username, "password123")
        
        # Ir al formulario de edición del evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/edit/")
        
        # Cambiar el venue del evento
        self.page.select_option("select[name='venue']", str(self.new_venue.id))
        
        # Enviar el formulario
        self.page.locator("button:has-text('Guardar Cambios')").click()
        
        # Verificar redirección
        self.page.wait_for_url(f"{self.live_server_url}/events/*")
        
        # Verificar que se creó la notificación
        notifications = Notification.objects.filter(
            title="Cambio en evento",
            event=self.event
        )
        self.assertEqual(notifications.count(), 1)
        
        # Verificar que el usuario con ticket recibió la notificación
        notification_users = NotificationUser.objects.filter(
            notification=notifications.first(),
            user=self.user_with_ticket
        )
        self.assertEqual(notification_users.count(), 1)

    def test_user_can_see_notification_in_ui(self):
        """Verifica que el usuario con ticket puede ver la notificación en la interfaz"""
        self.context.clear_cookies()
        
        # Como organizador
        self.login_user(self.organizer.username, "password123")
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/edit/")
        
        # Cambiar fecha
        new_date = (self.event.scheduled_at + timedelta(days=5)).date()
        self.page.fill("input[name='date']", new_date.strftime("%Y-%m-%d"))
        self.page.locator("button:has-text('Guardar Cambios')").click()
        
        # Nueva sesión
        self.context.close()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Login como usuario con ticket
        self.login_user(self.user_with_ticket.username, "password123")
        
        # ir a la vista de notificaciones
        self.page.goto(f"{self.live_server_url}/notifications/visualizacion")
        
        # Ver contenido
        print(self.page.content())
        
        # Verificar que se ve la notificación
        expect(self.page.locator("body")).to_contain_text("Se modificó la fecha/hora o el lugar del evento.")
